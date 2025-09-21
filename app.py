import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import os
import requests
import threading
from github import Github, GithubException
import base64

# --- Constants ---
TOKEN_FILE = "github_token.txt"
COMMON_LICENSES = {
    "None": "",
    "MIT License": "mit",
    "GNU GPLv3": "gpl-3.0",
    "Apache License 2.0": "apache-2.0",
    "BSD 3-Clause License": "bsd-3-clause",
    "Unlicense": "unlicense",
}

class GithubApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("GitHub Repository Manager")
        self.geometry("1200x800")

        self.github_api = None
        self.user = None
        self.current_repo_browser_path = ""

        self._create_widgets()
        self._load_token()
        self._update_ui_state()

    def _create_widgets(self):
        # --- Top Frame for Authentication ---
        top_frame = ttk.Frame(self, padding="10")
        top_frame.pack(fill=tk.X)
        
        ttk.Label(top_frame, text="GitHub Token:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.token_entry = ttk.Entry(top_frame, width=50, show="*")
        self.token_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        
        self.save_token_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(top_frame, text="Save Token", variable=self.save_token_var).grid(row=0, column=2, padx=5)

        self.login_button = ttk.Button(top_frame, text="Login", command=self._login)
        self.login_button.grid(row=0, column=3, padx=5)
        
        self.login_status_label = ttk.Label(top_frame, text="Not logged in.")
        self.login_status_label.grid(row=0, column=4, padx=10, sticky="w")
        top_frame.columnconfigure(1, weight=1)

        # --- Main Paned Window ---
        main_pane = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        main_pane.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # --- Left Pane: Repository List ---
        repo_list_frame = ttk.Frame(main_pane, padding="5")
        
        ttk.Button(repo_list_frame, text="Refresh Repositories", command=self._list_repos).pack(fill=tk.X, pady=5)
        
        repo_scrollbar_y = ttk.Scrollbar(repo_list_frame, orient=tk.VERTICAL)
        self.repo_listbox = tk.Listbox(repo_list_frame, yscrollcommand=repo_scrollbar_y.set)
        repo_scrollbar_y.config(command=self.repo_listbox.yview)
        
        self.repo_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        repo_scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        self.repo_listbox.bind("<<ListboxSelect>>", self._on_repo_select)

        main_pane.add(repo_list_frame, weight=1)

        # --- Right Pane: Notebook with Actions ---
        notebook = ttk.Notebook(main_pane)
        main_pane.add(notebook, weight=3)
        
        # Tab 1: Repo Browser (NEW)
        self._create_repo_browser_tab(notebook)

        # Tab 2: Repo Actions
        self._create_repo_actions_tab(notebook)
        
        # Tab 3: Create Repo
        self._create_new_repo_tab(notebook)
        
        # --- Bottom Frame for Logging ---
        log_frame = ttk.Frame(self, padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True)
        ttk.Label(log_frame, text="Log:").pack(anchor="w")
        
        log_scrollbar = ttk.Scrollbar(log_frame)
        self.log_text = tk.Text(log_frame, height=10, state="disabled", yscrollcommand=log_scrollbar.set)
        log_scrollbar.config(command=self.log_text.yview)
        
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        log_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def _create_repo_browser_tab(self, notebook):
        browser_tab = ttk.Frame(notebook, padding="10")
        notebook.add(browser_tab, text="Repository Browser")

        # Top controls
        browser_controls_frame = ttk.Frame(browser_tab)
        browser_controls_frame.pack(fill=tk.X, pady=5)

        self.browser_up_button = ttk.Button(browser_controls_frame, text="⬆️ Go Up", command=self._browser_go_up)
        self.browser_up_button.pack(side=tk.LEFT, padx=5)

        self.browser_refresh_button = ttk.Button(browser_controls_frame, text="🔄 Refresh", command=self._browser_refresh)
        self.browser_refresh_button.pack(side=tk.LEFT, padx=5)

        self.browser_path_label = ttk.Label(browser_controls_frame, text="Current Path: /", anchor="w")
        self.browser_path_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)

        # Main treeview
        tree_frame = ttk.Frame(browser_tab)
        tree_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.repo_tree = ttk.Treeview(tree_frame, columns=("Type", "Size"), show="headings")
        self.repo_tree.heading("Type", text="Type")
        self.repo_tree.heading("Size", text="Size")
        self.repo_tree.column("Type", width=80, anchor="center")
        self.repo_tree.column("Size", width=100, anchor="e")

        # Add a hidden 'Path' column
        self.repo_tree['columns'] = ('Name', 'Type', 'Size', 'Path')
        self.repo_tree.heading('Name', text='Name')
        self.repo_tree.heading('Type', text='Type')
        self.repo_tree.heading('Size', text='Size')
        self.repo_tree.heading('Path', text='Path')
        self.repo_tree.column('Path', width=0, stretch=tk.NO) # Hide the Path column
        self.repo_tree.column('Name', width=300)

        tree_scrollbar_y = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.repo_tree.yview)
        self.repo_tree.configure(yscrollcommand=tree_scrollbar_y.set)

        self.repo_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.repo_tree.bind("<Double-1>", self._on_tree_double_click)
        self.repo_tree.bind("<<TreeviewSelect>>", self._on_tree_select)

        # Bottom action buttons
        browser_actions_frame = ttk.Frame(browser_tab)
        browser_actions_frame.pack(fill=tk.X, pady=5)

        self.browser_view_button = ttk.Button(browser_actions_frame, text="View/Edit File...", command=self._browser_view_file)
        self.browser_view_button.pack(side=tk.LEFT, padx=5)

        self.browser_delete_button = ttk.Button(browser_actions_frame, text="Delete Selected...", command=self._browser_delete_item, style="danger.TButton")
        self.browser_delete_button.pack(side=tk.LEFT, padx=5)

    def _create_repo_actions_tab(self, notebook):
        actions_tab = ttk.Frame(notebook, padding="10")
        notebook.add(actions_tab, text="General Actions")
        
        # Selected Repo Info
        self.selected_repo_label = ttk.Label(actions_tab, text="Select a repository from the list.", font=("", 10, "bold"))
        self.selected_repo_label.pack(anchor="w", pady=(0, 10))

        # Action Buttons
        btn_frame = ttk.Frame(actions_tab)
        btn_frame.pack(fill=tk.X, pady=5)
        self.download_button = ttk.Button(btn_frame, text="Download as .zip", command=self._download_repo)
        self.download_button.pack(side=tk.LEFT, padx=5)
        self.delete_repo_button = ttk.Button(btn_frame, text="Delete Repository", command=self._delete_repo, style="danger.TButton")
        self.delete_repo_button.pack(side=tk.LEFT, padx=5)
        
        # File/Folder Operations
        file_ops_frame = ttk.LabelFrame(actions_tab, text="Bulk Upload Operations", padding="10")
        file_ops_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        ttk.Label(file_ops_frame, text="Remote Path (in repo):").grid(row=0, column=0, sticky="w", pady=2)
        self.remote_path_entry = ttk.Entry(file_ops_frame, width=50)
        self.remote_path_entry.grid(row=1, column=0, columnspan=2, sticky="ew", pady=2)
        self.remote_path_entry.insert(0, "path/to/upload_destination")
        
        self.upload_file_button = ttk.Button(file_ops_frame, text="Upload File...", command=self._upload_file)
        self.upload_file_button.grid(row=2, column=0, sticky="ew", padx=2, pady=5)

        self.upload_folder_button = ttk.Button(file_ops_frame, text="Upload Folder...", command=self._upload_folder)
        self.upload_folder_button.grid(row=2, column=1, sticky="ew", padx=2, pady=5)
        
        file_ops_frame.columnconfigure(0, weight=1)
        file_ops_frame.columnconfigure(1, weight=1)
        
        # Style for danger button
        s = ttk.Style()
        s.configure("danger.TButton", foreground="red")


    def _create_new_repo_tab(self, notebook):
        create_tab = ttk.Frame(notebook, padding="10")
        notebook.add(create_tab, text="Create New Repository")
        
        ttk.Label(create_tab, text="Repository Name:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.new_repo_name = ttk.Entry(create_tab, width=40)
        self.new_repo_name.grid(row=0, column=1, sticky="ew", padx=5, pady=5)

        ttk.Label(create_tab, text="Description (optional):").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.new_repo_desc = ttk.Entry(create_tab, width=40)
        self.new_repo_desc.grid(row=1, column=1, sticky="ew", padx=5, pady=5)

        self.new_repo_private = tk.BooleanVar(value=True)
        ttk.Checkbutton(create_tab, text="Private Repository", variable=self.new_repo_private).grid(row=2, column=1, sticky="w", padx=5, pady=5)

        self.new_repo_readme = tk.BooleanVar(value=True)
        ttk.Checkbutton(create_tab, text="Initialize with a README.md", variable=self.new_repo_readme).grid(row=3, column=1, sticky="w", padx=5, pady=5)

        ttk.Label(create_tab, text="Add .gitignore:").grid(row=4, column=0, sticky="w", padx=5, pady=5)
        self.new_repo_gitignore = ttk.Entry(create_tab, width=40)
        self.new_repo_gitignore.grid(row=4, column=1, sticky="ew", padx=5, pady=5)
        self.new_repo_gitignore.insert(0, "Python")

        ttk.Label(create_tab, text="Choose a license:").grid(row=5, column=0, sticky="w", padx=5, pady=5)
        self.new_repo_license = ttk.Combobox(create_tab, values=list(COMMON_LICENSES.keys()), state="readonly")
        self.new_repo_license.grid(row=5, column=1, sticky="ew", padx=5, pady=5)
        self.new_repo_license.set("MIT License")
        
        self.create_repo_button = ttk.Button(create_tab, text="Create Repository", command=self._create_repo)
        self.create_repo_button.grid(row=6, column=1, sticky="e", padx=5, pady=10)

        create_tab.columnconfigure(1, weight=1)

    # --- UI State Management ---

    def _update_ui_state(self, busy=False):
        """Enable/disable widgets based on login status and selection."""
        is_logged_in = self.github_api is not None
        is_repo_selected = bool(self.repo_listbox.curselection())
        
        # General state
        self.create_repo_button.config(state=tk.NORMAL if is_logged_in and not busy else tk.DISABLED)
        
        repo_action_state = tk.NORMAL if is_logged_in and is_repo_selected and not busy else tk.DISABLED
        self.download_button.config(state=repo_action_state)
        self.delete_repo_button.config(state=repo_action_state)
        self.upload_file_button.config(state=repo_action_state)
        self.upload_folder_button.config(state=repo_action_state)
        
        # Browser state
        self.browser_refresh_button.config(state=repo_action_state)
        self.browser_up_button.config(state=tk.NORMAL if is_logged_in and is_repo_selected and self.current_repo_browser_path and not busy else tk.DISABLED)
        
        # Browser selection-dependent state
        tree_selection = self.repo_tree.selection()
        is_tree_item_selected = bool(tree_selection)
        item_type = ""
        if is_tree_item_selected:
            item_values = self.repo_tree.item(tree_selection[0], 'values')
            if item_values:
                item_type = item_values[1] # Type is the second column

        browser_selection_state = tk.NORMAL if is_repo_selected and is_tree_item_selected and not busy else tk.DISABLED
        self.browser_delete_button.config(state=browser_selection_state)
        self.browser_view_button.config(state=tk.NORMAL if browser_selection_state == tk.NORMAL and item_type == 'File' else tk.DISABLED)

        # Handle login button state
        self.login_button.config(state=tk.DISABLED if busy else tk.NORMAL)
        
        # Update cursor for busy state
        self.config(cursor="watch" if busy else "")

    def _on_repo_select(self, event=None):
        """Update UI when a repository is selected."""
        if not self.repo_listbox.curselection():
            self.selected_repo_label.config(text="Select a repository from the list.")
            # Clear browser
            self.repo_tree.delete(*self.repo_tree.get_children())
            self.browser_path_label.config(text="Current Path: /")
            self._update_ui_state()
            return

        selected_index = self.repo_listbox.curselection()[0]
        repo_name = self.repo_listbox.get(selected_index)
        self.selected_repo_label.config(text=f"Selected: {repo_name}")
        
        # Load root of the selected repo in the browser tab
        self._browse_repo(path="")

    def _on_tree_select(self, event=None):
        self._update_ui_state()
        
    def _on_tree_double_click(self, event=None):
        selection = self.repo_tree.selection()
        if not selection: return
        
        item = self.repo_tree.item(selection[0])
        item_type = item['values'][1]
        item_path = item['values'][3]

        if item_type == 'Directory':
            self._browse_repo(path=item_path)
        elif item_type == 'File':
            self._browser_view_file()

    # --- Core Logic in Threads ---

    def _run_in_thread(self, target_func, *args, **kwargs):
        """Helper to run a function in a new thread to avoid freezing the GUI."""
        self._update_ui_state(busy=True)
        # Pass both args and kwargs to the Thread constructor
        thread = threading.Thread(target=target_func, args=args, kwargs=kwargs)
        thread.daemon = True
        thread.start()
        self._check_thread(thread)

    def _check_thread(self, thread):
        """Check if the thread is alive and re-enable UI when it's done."""
        if thread.is_alive():
            self.after(100, lambda: self._check_thread(thread))
        else:
            self._update_ui_state(busy=False)

    def _log(self, message):
        """Thread-safe logging to the text widget."""
        def append_log():
            self.log_text.config(state="normal")
            self.log_text.insert(tk.END, message + "\n")
            self.log_text.see(tk.END)
            self.log_text.config(state="disabled")
        self.after(0, append_log)

    # --- Authentication and Repo Listing ---
    
    def _load_token(self):
        if os.path.exists(TOKEN_FILE):
            with open(TOKEN_FILE, "r") as f:
                token = f.read().strip()
                if token:
                    self.token_entry.insert(0, token)
                    self._log(f"Loaded token from {TOKEN_FILE}.")
                    self._run_in_thread(self._login_logic)

    def _save_token(self, token):
        if self.save_token_var.get():
            with open(TOKEN_FILE, "w") as f:
                f.write(token)
            self._log(f"Token saved to {TOKEN_FILE}.")
        elif os.path.exists(TOKEN_FILE):
             os.remove(TOKEN_FILE)
             self._log(f"Removed {TOKEN_FILE}.")

    def _login(self): self._run_in_thread(self._login_logic)
    def _list_repos(self): self._run_in_thread(self._list_repos_logic)

    def _login_logic(self):
        token = self.token_entry.get().strip()
        if not token:
            self._log("❌ Error: GitHub token cannot be empty.")
            return

        try:
            self.github_api = Github(token)
            self.user = self.github_api.get_user()
            self.user.login # This call will fail if the token is invalid
            self.after(0, lambda: self.login_status_label.config(text=f"Logged in as: {self.user.login}", foreground="green"))
            self._log(f"✅ Successfully logged in as {self.user.login}.")
            self._save_token(token)
            self._run_in_thread(self._list_repos_logic) # Automatically list repos on login
        except Exception as e:
            self.github_api = None
            self.user = None
            self.after(0, lambda: self.login_status_label.config(text="Login failed.", foreground="red"))
            self._log(f"❌ Login failed: {e}")

    def _list_repos_logic(self):
        if not self.user:
            self._log("❌ Error: Not logged in.")
            return

        self._log("🔄 Fetching repositories...")
        repos = self.user.get_repos()
        repo_names = sorted([repo.full_name for repo in repos])
        
        def update_listbox():
            current_selection = self._get_selected_repo_name()
            self.repo_listbox.delete(0, tk.END)
            for name in repo_names:
                self.repo_listbox.insert(tk.END, name)
            if current_selection in repo_names:
                idx = repo_names.index(current_selection)
                self.repo_listbox.selection_set(idx)
                self.repo_listbox.activate(idx)

            self._log(f"✅ Found {len(repo_names)} repositories.")
            self._on_repo_select() 
        
        self.after(0, update_listbox)
        
    def _get_selected_repo_name(self):
        if not self.repo_listbox.curselection():
            return None
        return self.repo_listbox.get(self.repo_listbox.curselection()[0])

    # --- Browser Tab Logic ---

    def _browse_repo(self, path=""):
        repo_name = self._get_selected_repo_name()
        if not repo_name: return
        self._run_in_thread(self._browse_repo_logic, repo_name, path)

    def _browse_repo_logic(self, repo_name, path):
        self._log(f"🔎 Browsing '{repo_name}' at path: '{path or '/'}'...")
        try:
            repo = self.github_api.get_repo(repo_name)
            contents = repo.get_contents(path)
            
            self.current_repo_browser_path = path
            
            # Sort directories first, then files, all alphabetically
            sorted_contents = sorted(contents, key=lambda c: (c.type != 'dir', c.name.lower()))
            
            def update_tree():
                self.repo_tree.delete(*self.repo_tree.get_children())
                self.browser_path_label.config(text=f"Current Path: /{path}")
                
                for item in sorted_contents:
                    item_type = "Directory" if item.type == 'dir' else "File"
                    item_size = self._format_size(item.size) if item.type == 'file' else ""
                    # The hidden path column holds the full path for later use
                    self.repo_tree.insert("", "end", values=(item.name, item_type, item_size, item.path))
                
                self._log(f"✅ Loaded {len(sorted_contents)} items.")

            self.after(0, update_tree)
        except Exception as e:
            self._log(f"❌ Failed to browse repository contents: {e}")

    def _browser_go_up(self):
        if not self.current_repo_browser_path: return
        parent_path = os.path.dirname(self.current_repo_browser_path)
        self._browse_repo(path=parent_path)
    
    def _browser_refresh(self):
        self._browse_repo(path=self.current_repo_browser_path)

    def _browser_view_file(self):
        selection = self.repo_tree.selection()
        if not selection: return
        
        item = self.repo_tree.item(selection[0])
        item_path = item['values'][3]
        repo_name = self._get_selected_repo_name()
        
        self._run_in_thread(self._view_file_logic, repo_name, item_path)
    
    def _view_file_logic(self, repo_name, path):
        self._log(f"📖 Opening file '{path}'...")
        try:
            repo = self.github_api.get_repo(repo_name)
            file_content = repo.get_contents(path)
            
            content_decoded = ""
            try:
                content_decoded = file_content.decoded_content.decode('utf-8')
            except (UnicodeDecodeError, AttributeError):
                self._log("⚠️ Could not decode file content as UTF-8. It might be a binary file.")
                content_decoded = "[Binary file - cannot be displayed or edited]"

            self.after(0, self._show_file_editor_window, repo, file_content, content_decoded)
        except Exception as e:
            self._log(f"❌ Failed to open file: {e}")

    def _show_file_editor_window(self, repo, file_content_obj, content_text):
        editor_window = tk.Toplevel(self)
        editor_window.title(f"Editing: {file_content_obj.path}")
        editor_window.geometry("800x600")

        text_widget = scrolledtext.ScrolledText(editor_window, wrap=tk.WORD, font=("", 10))
        text_widget.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        text_widget.insert("1.0", content_text)
        
        # Disable editing for binary files
        if "[Binary file" in content_text:
            text_widget.config(state="disabled")

        def save_changes():
            new_content = text_widget.get("1.0", tk.END)
            # Pass required info to the logic function
            self._run_in_thread(self._save_file_changes_logic, repo, file_content_obj, new_content)
            editor_window.destroy()

        button_frame = ttk.Frame(editor_window, padding=10)
        button_frame.pack(fill=tk.X)
        
        save_button = ttk.Button(button_frame, text="Save Changes", command=save_changes)
        if "[Binary file" in content_text:
            save_button.config(state="disabled")
        save_button.pack(side=tk.RIGHT, padx=5)
        
        ttk.Button(button_frame, text="Close", command=editor_window.destroy).pack(side=tk.RIGHT)

    def _save_file_changes_logic(self, repo, file_content_obj, new_content):
        self._log(f"💾 Saving changes to '{file_content_obj.path}'...")
        try:
            repo.update_file(
                path=file_content_obj.path,
                message=f"docs: update {file_content_obj.name} via GUI",
                content=new_content,
                sha=file_content_obj.sha
            )
            self._log("✅ File saved successfully.")
            # Refresh the browser to show new size/date if applicable
            self._browser_refresh()
        except Exception as e:
            self._log(f"❌ Failed to save changes: {e}")

    def _browser_delete_item(self):
        selection = self.repo_tree.selection()
        if not selection: return
        
        item = self.repo_tree.item(selection[0])
        item_path = item['values'][3]
        item_type = item['values'][1]
        repo_name = self._get_selected_repo_name()

        if not messagebox.askyesno(
            f"Confirm Delete",
            f"Are you sure you want to PERMANENTLY DELETE the {item_type.lower()} '{item_path}' from '{repo_name}'?"
        ):
            self._log("Cancelled item deletion.")
            return

        self._run_in_thread(self._delete_path_logic, repo_name, item_path, refresh_on_complete=True)

    def _format_size(self, size_bytes):
        if size_bytes == 0:
            return "0 B"
        size_name = ("B", "KB", "MB", "GB", "TB")
        import math
        i = int(math.floor(math.log(size_bytes, 1024)))
        p = math.pow(1024, i)
        s = round(size_bytes / p, 2)
        return f"{s} {size_name[i]}"

    # --- General Actions & Create Repo Logic (largely unchanged) ---

    def _download_repo(self):
        repo_name = self._get_selected_repo_name()
        if not repo_name: return
        
        save_path = filedialog.asksaveasfilename(
            defaultextension=".zip",
            initialfile=f"{repo_name.split('/')[1]}.zip",
            filetypes=[("Zip files", "*.zip")]
        )
        if not save_path:
            self._log("Cancelled download.")
            return
            
        self._run_in_thread(self._download_repo_logic, repo_name, save_path)
    
    def _download_repo_logic(self, repo_name, save_path):
        try:
            repo = self.github_api.get_repo(repo_name)
            zip_url = repo.get_archive_link("zipball")
            self._log(f"⬇️ Downloading from {zip_url}...")
            
            response = requests.get(zip_url, allow_redirects=True)
            response.raise_for_status()
            
            with open(save_path, 'wb') as f:
                f.write(response.content)
            
            self._log(f"✅ Repository '{repo_name}' downloaded to '{save_path}'.")
        except Exception as e:
            self._log(f"❌ Download failed: {e}")

    def _create_repo(self): self._run_in_thread(self._create_repo_logic)
    def _create_repo_logic(self):
        name = self.new_repo_name.get().strip()
        if not name:
            self._log("❌ Error: Repository name is required."); return
            
        desc = self.new_repo_desc.get().strip()
        private = self.new_repo_private.get()
        auto_init = self.new_repo_readme.get()
        gitignore = self.new_repo_gitignore.get().strip()
        license_key = COMMON_LICENSES[self.new_repo_license.get()]

        self._log(f"🚀 Creating repository '{name}'...")
        try:
            self.user.create_repo(
                name=name, description=desc, private=private, auto_init=auto_init,
                gitignore_template=gitignore or None, license_template=license_key or None
            )
            self._log(f"✅ Successfully created repository: {self.user.login}/{name}")
            self._run_in_thread(self._list_repos_logic) # Refresh repo list
        except Exception as e:
            self._log(f"❌ Failed to create repository: {e}")

    def _delete_repo(self):
        repo_name = self._get_selected_repo_name()
        if not repo_name: return
        
        if not messagebox.askyesno("Confirm Delete", f"PERMANENTLY DELETE '{repo_name}'?\nThis cannot be undone."):
            self._log("Cancelled repository deletion."); return

        self._run_in_thread(self._delete_repo_logic, repo_name)

    def _delete_repo_logic(self, repo_name):
        self._log(f"🔥 Deleting repository '{repo_name}'...")
        try:
            repo = self.github_api.get_repo(repo_name)
            repo.delete()
            self._log(f"✅ Successfully deleted repository: {repo_name}")
            self._run_in_thread(self._list_repos_logic)
        except Exception as e:
            self._log(f"❌ Failed to delete repository: {e}")

    def _upload_file(self):
        repo_name = self._get_selected_repo_name();
        if not repo_name: return
        local_path = filedialog.askopenfilename()
        if not local_path: self._log("Cancelled file upload."); return

        remote_path = self.remote_path_entry.get().strip()
        if not remote_path or remote_path == "path/to/upload_destination":
            remote_path = os.path.basename(local_path)
            self.remote_path_entry.delete(0, tk.END)
            self.remote_path_entry.insert(0, remote_path)
        
        self._run_in_thread(self._upload_file_logic, repo_name, local_path, remote_path)

    def _upload_file_logic(self, repo_name, local_path, remote_path):
        self._log(f"🔼 Uploading '{local_path}' to '{repo_name}/{remote_path}'...")
        try:
            repo = self.github_api.get_repo(repo_name)
            with open(local_path, "rb") as f:
                content = f.read()
            try:
                file_contents = repo.get_contents(remote_path)
                repo.update_file(path=remote_path, message=f"feat: update {os.path.basename(remote_path)}", content=content, sha=file_contents.sha)
                self._log(f"✅ Successfully updated file: {remote_path}")
            except GithubException as e:
                if e.status == 404: # Not Found
                    repo.create_file(path=remote_path, message=f"feat: add {os.path.basename(remote_path)}", content=content)
                    self._log(f"✅ Successfully created file: {remote_path}")
                else: raise e
        except Exception as e: self._log(f"❌ Failed to upload file: {e}")

    def _upload_folder(self):
        repo_name = self._get_selected_repo_name();
        if not repo_name: return
        local_folder = filedialog.askdirectory()
        if not local_folder: self._log("Cancelled folder upload."); return
        remote_base_path = self.remote_path_entry.get().strip()
        self._run_in_thread(self._upload_folder_logic, repo_name, local_folder, remote_base_path)

    def _upload_folder_logic(self, repo_name, local_folder, remote_base_path):
        self._log(f"🔼 Starting folder upload from '{local_folder}'...")
        repo = self.github_api.get_repo(repo_name)
        for root, _, files in os.walk(local_folder):
            for file in files:
                local_path = os.path.join(root, file)
                relative_path = os.path.relpath(local_path, local_folder)
                remote_path = os.path.join(remote_base_path, relative_path).replace("\\", "/")
                self._log(f"   -> Uploading {remote_path}")
                try:
                    with open(local_path, 'rb') as f: content = f.read()
                    repo.create_file(path=remote_path, message=f"feat: add {file}", content=content)
                except GithubException as e:
                    if e.status == 422: self._log(f"   - ⚠️ Skipping '{remote_path}', already exists.")
                    else: self._log(f"   - ❌ Failed to upload '{local_path}': {e}")
                except Exception as e: self._log(f"   - ❌ Failed to upload '{local_path}': {e}")
        self._log("✅ Folder upload process complete.")

    def _delete_path_logic(self, repo_name, remote_path, refresh_on_complete=False):
        self._log(f"🔥 Deleting '{remote_path}' from '{repo_name}'...")
        try:
            repo = self.github_api.get_repo(repo_name)
            contents = repo.get_contents(remote_path)
            
            if isinstance(contents, list):
                self._log("   - It's a directory, deleting contents recursively...")
                # Note: GitHub API doesn't have a recursive delete. We must delete files one by one.
                # A more robust implementation would handle this, but this is a complex task.
                # For now, we rely on the helper which can delete one item at a time.
                # This code will fail on non-empty directories as get_contents is for a single path.
                # A proper recursive delete is needed here for folders.
                # For simplicity, this will only work if the API is smart or folder is empty.
                # Let's call the delete_file method on the *directory's sha*
                # THIS IS A SIMPLIFICATION. Real recursive delete is harder.
                # For this app, we'll assume deleting a folder means deleting items one by one.
                # A better approach:
                all_files_in_dir = []
                dir_contents = [contents]
                while dir_contents:
                    current_dir = dir_contents.pop(0)
                    for item in current_dir:
                        if item.type == 'dir':
                            dir_contents.append(repo.get_contents(item.path))
                        all_files_in_dir.append(item)
                
                for item in sorted(all_files_in_dir, key=lambda i: i.path, reverse=True):
                    self._log(f"   - Deleting {item.path}")
                    repo.delete_file(item.path, f"chore: remove {item.name}", item.sha)

                self._log(f"✅ Successfully deleted folder and contents: {remote_path}")

            else: # It's a single file
                repo.delete_file(contents.path, f"chore: remove {contents.name}", contents.sha)
                self._log(f"✅ Successfully deleted file: {remote_path}")
            
            if refresh_on_complete:
                self.after(100, self._browser_refresh)

        except GithubException as e:
            if e.status == 404: self._log(f"❌ Error: Path '{remote_path}' not found.")
            else: self._log(f"❌ Error deleting path: {e}")
        except Exception as e:
            self._log(f"❌ An unexpected error occurred: {e}")


if __name__ == "__main__":
    app = GithubApp()
    app.mainloop()