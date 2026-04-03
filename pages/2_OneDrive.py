"""
OneDrive Integration - Streamlit Page

Connect to OneDrive, browse folders, and sync documents
into the knowledge base.
"""

import streamlit as st
import os
from src.onedrive import (
    get_access_token,
    start_device_code_auth,
    complete_device_code_auth,
    get_user_info,
    list_folder,
    download_file,
    download_folder,
    disconnect,
)
from src.loader import load_documents, split_documents
from src.vectorstore import ingest_documents
from src.config import DOCS_DIR


st.set_page_config(
    page_title="OneDrive Integration",
    page_icon="☁️",
    layout="wide",
)

st.markdown("# ☁️ OneDrive Integration")
st.markdown("Connect to your OneDrive to sync documents into the knowledge base.")


# --- Session State ---
if "onedrive_token" not in st.session_state:
    st.session_state.onedrive_token = get_access_token()
if "onedrive_auth_flow" not in st.session_state:
    st.session_state.onedrive_auth_flow = None
if "current_folder" not in st.session_state:
    st.session_state.current_folder = "/"
if "folder_history" not in st.session_state:
    st.session_state.folder_history = ["/"]


# --- Authentication ---
if not st.session_state.onedrive_token:
    st.markdown("### Connect to OneDrive")
    st.markdown("You'll need to sign in with your Microsoft account to access your files.")

    if st.session_state.onedrive_auth_flow is None:
        if st.button("🔗 Connect to OneDrive", use_container_width=True):
            try:
                flow = start_device_code_auth()
                st.session_state.onedrive_auth_flow = flow
                st.rerun()
            except Exception as e:
                st.error(f"Failed to start authentication: {e}")
    else:
        flow = st.session_state.onedrive_auth_flow
        st.info(f"👉 Go to **https://microsoft.com/devicelogin** and enter code: **{flow['user_code']}**")
        st.markdown("After you've entered the code and signed in, click the button below.")

if st.button("✅ I've completed sign-in", use_container_width=True):
    with st.spinner("Waiting for Microsoft to confirm sign-in... this may take up to 30 seconds"):
        try:
            token = complete_device_code_auth(flow, timeout=120)
            st.session_state.onedrive_token = token
            st.session_state.onedrive_auth_flow = None
            st.success("Connected to OneDrive!")
            st.rerun()
        except Exception as e:
            st.error(f"Authentication failed: {e}")
            st.session_state.onedrive_auth_flow = None

        st.markdown("*Make sure you've signed in at microsoft.com/devicelogin before clicking the button above.*")

else:
    # --- Connected State ---
    # User info
    try:
        user = get_user_info(st.session_state.onedrive_token)
        col1, col2 = st.columns([3, 1])
        with col1:
            st.success(f"Connected as **{user.get('displayName', 'Unknown')}** ({user.get('mail', user.get('userPrincipalName', ''))})")
        with col2:
            if st.button("🔌 Disconnect"):
                disconnect()
                st.session_state.onedrive_token = None
                st.session_state.current_folder = "/"
                st.session_state.folder_history = ["/"]
                st.rerun()
    except Exception:
        st.warning("Session expired. Please reconnect.")
        st.session_state.onedrive_token = None
        st.rerun()

    st.markdown("---")

    # --- Folder Navigation ---
    current = st.session_state.current_folder
    st.markdown(f"### 📁 Browsing: `{current}`")

    # Navigation buttons
    nav_col1, nav_col2, nav_col3 = st.columns([1, 1, 4])
    with nav_col1:
        if current != "/" and st.button("⬆️ Up one level"):
            parent = "/".join(current.rstrip("/").split("/")[:-1]) or "/"
            st.session_state.current_folder = parent
            st.rerun()
    with nav_col2:
        if st.button("🏠 Root"):
            st.session_state.current_folder = "/"
            st.rerun()

    # Quick navigation
    quick_folder = st.text_input(
        "Go to folder path:",
        placeholder="/Documents/AI Projects",
        key="folder_nav",
    )
    if quick_folder and st.button("Go"):
        st.session_state.current_folder = quick_folder
        st.rerun()

    st.markdown("---")

    # --- File Listing ---
    try:
        items = list_folder(st.session_state.onedrive_token, current)

        if not items:
            st.info("This folder is empty.")
        else:
            # Separate folders and files
            folders = [i for i in items if i["is_folder"]]
            files = [i for i in items if not i["is_folder"]]

            # Display folders
            if folders:
                st.markdown("#### 📁 Folders")
                for folder in folders:
                    col1, col2 = st.columns([4, 1])
                    with col1:
                        st.markdown(f"📁 **{folder['name']}** ({folder.get('child_count', '?')} items)")
                    with col2:
                        if st.button("Open", key=f"open_{folder['id']}"):
                            st.session_state.current_folder = folder["path"]
                            st.rerun()

            # Display files
            if files:
                st.markdown("#### 📄 Files")

                # Select all supported files
                supported_files = [f for f in files if f.get("supported", False)]
                unsupported_files = [f for f in files if not f.get("supported", False)]

                if supported_files:
                    # Batch download option
                    st.markdown(f"**{len(supported_files)} supported files** in this folder")

                    if st.button(
                        f"⬇️ Download all {len(supported_files)} supported files & ingest",
                        use_container_width=True,
                    ):
                        progress = st.progress(0, text="Downloading files...")
                        downloaded = []

                        for i, file in enumerate(supported_files):
                            progress.progress(
                                (i + 1) / len(supported_files),
                                text=f"Downloading {file['name']}...",
                            )
                            try:
                                path = download_file(
                                    st.session_state.onedrive_token,
                                    file["id"],
                                    file["name"],
                                )
                                downloaded.append(path)
                            except Exception as e:
                                st.warning(f"Failed to download {file['name']}: {e}")

                        if downloaded:
                            progress.progress(1.0, text="Ingesting into knowledge base...")
                            docs = load_documents()
                            if docs:
                                chunks = split_documents(docs)
                                ingest_documents(chunks)
                                st.success(
                                    f"Downloaded {len(downloaded)} files and ingested "
                                    f"{len(chunks)} chunks into the knowledge base!"
                                )
                            else:
                                st.warning("Files downloaded but no content could be extracted.")
                        progress.empty()

                    st.markdown("")

                # Individual file listing
                for file in files:
                    size_kb = file["size"] / 1024
                    supported_badge = "✅" if file.get("supported") else "⚠️"

                    col1, col2, col3 = st.columns([4, 1, 1])
                    with col1:
                        st.markdown(
                            f"{supported_badge} **{file['name']}** "
                            f"({file.get('extension', '').upper().strip('.')}, {size_kb:.0f}KB)"
                        )
                    with col2:
                        if file.get("supported"):
                            if st.button("⬇️", key=f"dl_{file['id']}", help="Download this file"):
                                with st.spinner(f"Downloading {file['name']}..."):
                                    try:
                                        download_file(
                                            st.session_state.onedrive_token,
                                            file["id"],
                                            file["name"],
                                        )
                                        st.success(f"Downloaded {file['name']}")
                                    except Exception as e:
                                        st.error(f"Failed: {e}")

                if unsupported_files:
                    with st.expander(f"⚠️ {len(unsupported_files)} unsupported file(s)"):
                        for file in unsupported_files:
                            st.markdown(f"- {file['name']} ({file.get('extension', 'unknown')})")

    except Exception as e:
        st.error(f"Error listing folder: {e}")
        if "401" in str(e) or "token" in str(e).lower():
            st.session_state.onedrive_token = None
            st.rerun()
