# GithubApp

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A desktop application built with Python and Tkinter that provides a graphical user interface for managing your GitHub repositories.

This tool allows you to perform common repository actions like creating, deleting, downloading, and browsing repositories without leaving a comfortable GUI. It features a built-in file browser to view, edit, upload, and delete files directly within your repositories.

## Screenshot

*(It is highly recommended to add a screenshot of your application here)*

![App Screenshot](./screenshot.png)

## Features

-   **Secure Authentication**: Login using a GitHub Personal Access Token (PAT). Your token can be optionally saved locally for future sessions.
-   **Repository Management**:
    -   List all your public and private repositories.
    -   Create new repositories with options for a README, .gitignore, and license.
    -   Delete repositories with confirmation.
    -   Download any repository as a `.zip` archive.
-   **Remote File Browser**:
    -   Navigate the file and folder structure of any selected repository.
    -   View file sizes and types at a glance.
    -   Go up directories or refresh the current view.
-   **File Operations**:
    -   **View & Edit**: Open and edit text-based files in a new window and commit changes directly.
    -   **Upload**: Upload individual files or entire folders to any location within a repository.
    -   **Delete**: Delete files or folders from your repository.
-   **User-Friendly Interface**:
    -   A tabbed interface to keep actions organized.
    -   A persistent log window to see the status of all operations.
    -   A non-blocking UI that remains responsive during network operations (e.g., downloads, uploads).

## Requirements

-   Python 3.6+
-   The required Python packages are listed in `requirements.txt`:
    -   `PyGithub`
    -   `requests`

## Installation & Setup

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/azario0/GithubApp.git
    cd GithubApp
    ```

2.  **Install dependencies:**
    It's recommended to use a virtual environment.
    ```bash
    # Create and activate a virtual environment (optional but recommended)
    python -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`

    ```bash
    pip install PyGithub requests
    ```

3.  **Generate a GitHub Personal Access Token (PAT):**
    This application requires a PAT to interact with the GitHub API on your behalf.
    -   Go to your GitHub [Developer settings](https://github.com/settings/tokens).
    -   Click **"Generate new token"** (classic).
    -   Give your token a descriptive name (e.g., "GithubApp GUI").
    -   Set an expiration date.
    -   Under **"Select scopes"**, check the following permissions:
        -   `repo`: Full control of private repositories. This is the main one you need.
        -   `delete_repo`: Required for the "Delete Repository" functionality.
    -   Click **"Generate token"** and **copy the token immediately**. You will not be able to see it again.

## Usage

1.  **Run the application:**
    ```bash
    python app.py
    ```

2.  **Login:**
    -   Paste your GitHub Personal Access Token into the "GitHub Token" field.
    -   If you want the app to remember your token for the next launch, leave the "Save Token" box checked. The token will be saved to a `github_token.txt` file in the same directory.
    -   Click "Login". The status label will update, and your repositories will be loaded into the list on the left.

3.  **Perform Actions:**
    -   **Select a repository** from the list on the left to enable the action tabs on the right.
    -   Use the **"Repository Browser"** tab to navigate and manage files.
    -   Use the **"General Actions"** tab to download, delete, or perform bulk uploads.
    -   Use the **"Create New Repository"** tab to create a new repo on your account.
    -   Monitor the **Log** at the bottom for feedback on all operations.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

### Suggested `LICENSE` file content:

You should create a file named `LICENSE` in the root of your repository and paste the following content into it.

