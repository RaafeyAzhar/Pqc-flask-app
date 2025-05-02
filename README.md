# pqc-flask-app

A Flask web application demonstrating Post-Quantum Cryptography (PQC) using the $pqcLibraryName library.

## Project Setup

1.  **Clone the repository:**
    git clone <your-repo-url>
    cd pqc-flask-app

2.  **Create/Activate Virtual Environment:**
    * Windows:
        python -m venv .venv
        .\.venv\Scripts\activate
    * macOS/Linux:
        python3 -m venv .venv
        source .venv/bin/activate

3.  **Install Dependencies:**
    pip install -r requirements.txt

    **ðŸŸ¥ IMPORTANT: $pqcLibraryName Library Installation Troubleshooting ðŸŸ¥**

    *   The 
equirements.txt file includes $pqcLibraryName. pip *should* automatically install it.
    *   **Common Issue (Especially on Windows):** You might run pip install -r requirements.txt, see no errors, but then get ModuleNotFoundError: No module named 'pqcrypto.kem' (or similar for .sign) when running lask run.
    *   **Why?** This usually means the pre-compiled version (wheel) provided on PyPI for your specific combination of Windows, Python version, and architecture (e.g., 64-bit) is incomplete or faulty. It installs *something*, but not the necessary compiled submodules (kem, sign).
    *   **Troubleshooting Steps:**
        1.  **Activate Venv:** Double-check your virtual environment (.venv) is activated.
        2.  **Check Python/Pip:** Ensure you are using Python 3.9+ and pip is up-to-date (pip install --upgrade pip within the activated venv).
        3.  **Install Build Tools:** The most reliable fix is often to force pip to build the library from source. This **REQUIRES C/C++ build tools**:
            *   On **Windows:** Install **Build Tools for Visual Studio**. Download the installer from Microsoft's website and during installation, select the "**Desktop development with C++**" workload.
            *   On Debian/Ubuntu: sudo apt update && sudo apt install build-essential python3-dev
            *   On macOS: Install Xcode Command Line Tools (xcode-select --install).
        4.  **Reinstall Forcing Source Build:** After installing build tools, try reinstalling pqcrypto within your activated venv, telling pip *not* to use the pre-compiled wheel:
            pip install --force-reinstall --no-binary pqcrypto pqcrypto
            *(Note: Using :all: instead of $pqcLibraryName might be needed: pip install --force-reinstall --no-binary :all: pqcrypto)*
        5.  **Manual Build (Advanced):** If the above still fails, you might need to follow the manual build steps outlined in potential GitHub issues for the pqcrypto library (like cloning the repo, initializing submodules, running python compile.py, and manually copying files). This is complex and should be a last resort. Consult the library's official repository/documentation.
        6.  **Check Library Issues:** Look at the $pqcLibraryName GitHub repository's "Issues" section to see if others have reported similar problems for your environment.

4.  **Configure Environment Variables:**
    Copy .env.example to .env and fill in the required values (especially SECRET_KEY).
    * Windows PowerShell: Copy-Item .\.env.example .\.env
    * Windows Cmd: copy .env.example .env
    * macOS/Linux: cp .env.example .env

    *Edit .env with your actual secret key.* You can generate one using: python -c "import secrets; print(secrets.token_hex())"

5.  **Run the application:**
    lask run

    *If you encounter the ModuleNotFoundError mentioned in step 3, stop the server and perform the troubleshooting steps.*

6.  Open your browser and navigate to http://127.0.0.1:5000 (or the address provided by Flask).

## PQC Algorithm Used

* The pp.py file is configured to use $kemAlgorithm by default from the $pqcLibraryName library.
* This algorithm is one of the KEMs selected by NIST for standardization (ML-KEM). It offers a balance of security and performance.

## Application Functionality

* **Key Generation:** Uses the imported kem_generate_keypair() function for $kemAlgorithm.
* **Encryption (Encapsulation):** Uses the imported kem_encrypt() function.
* **Decryption (Decapsulation):** Uses the imported kem_decrypt() function.
* **If PQC Fails to Load:** The application will run but show warnings, and PQC operations will be disabled with error messages in the UI.
