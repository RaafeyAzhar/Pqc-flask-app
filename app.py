import os
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_talisman import Talisman
from dotenv import load_dotenv
import traceback # Import traceback for logging errors
import base64 # For potentially handling keys/ciphertext if hex causes issues (not used currently)
import secrets # For session key

# --- PQC Library Integration ---
PQC_LIBRARY_NAME = 'pqcrypto'
# --- CHOOSE YOUR ALGORITHM ---
# Select a KEM algorithm from the available list in the documentation
# Examples: 'ml_kem_512', 'ml_kem_768', 'hqc_128', 'mceliece348864f'
KEM_ALGORITHM = 'ml_kem_512' # <--- CHANGE THIS TO YOUR DESIRED KEM
# ---------------------------

PQC_ENABLED = False
kem_generate_keypair = None
kem_encrypt = None
kem_decrypt = None

try:
    # Dynamically import based on KEM_ALGORITHM
    kem_module_path = f'{PQC_LIBRARY_NAME}.kem.{KEM_ALGORITHM}'
    kem_module = __import__(kem_module_path, fromlist=['generate_keypair', 'encrypt', 'decrypt'])

    kem_generate_keypair = getattr(kem_module, 'generate_keypair')
    kem_encrypt = getattr(kem_module, 'encrypt')
    kem_decrypt = getattr(kem_module, 'decrypt')

    PQC_ENABLED = True
    print(f"Successfully imported KEM functions for algorithm: {KEM_ALGORITHM}")

# Catch if 'pqcrypto' itself is not installed OR the specific submodule/functions don't exist
except (ImportError, ModuleNotFoundError, AttributeError) as e:
    print(f"WARNING: Failed to import PQC functions for KEM '{KEM_ALGORITHM}'. Error: {e}")
    print(f"         Ensure '{PQC_LIBRARY_NAME}' is installed correctly (check README troubleshooting).")
    print(f"         Ensure the KEM_ALGORITHM name ('{KEM_ALGORITHM}') in app.py is correct and supported by the installed library.")
    print(f"         PQC functionality will be disabled.")
    PQC_ENABLED = False # Explicitly set to False
except Exception as e:
    # Catch any other unexpected errors during import/setup
    print(f"ERROR: Unexpected error initializing PQC library for KEM '{KEM_ALGORITHM}': {e}")
    traceback.print_exc()
    PQC_ENABLED = False

# --- Flask App Setup ---
load_dotenv() # Load environment variables from .env file

app = Flask(__name__)
# Use a secure, random secret key for sessions and WTForms
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', secrets.token_hex(16))
if app.config['SECRET_KEY'] == 'dev-secret-key-please-change': # Check if default was loaded from .env
     print("Warning: SECRET_KEY is using the default development key. Please set a unique key in your .env file.")

# --- Security Headers ---
# More restrictive CSP - adjust if you add external resources
csp = {
    'default-src': '\'self\'',
    'script-src': '\'self\'',
    'style-src': '\'self\'',
    'img-src': '\'self\' data:',
    'font-src': '\'self\'',
    'object-src': '\'none\'', # Disallow plugins like Flash
    'frame-ancestors': '\'none\'' # Prevent clickjacking
}
# Enable Talisman with HSTS, CSP, etc. Force HTTPS in production.
talisman = Talisman(
    app,
    content_security_policy=csp,
    force_https=os.environ.get('FLASK_ENV') == 'production', # Force HTTPS only in production
    strict_transport_security=os.environ.get('FLASK_ENV') == 'production', # Enable HSTS in production
    session_cookie_secure=os.environ.get('FLASK_ENV') == 'production', # Secure cookie flag
    session_cookie_httponly=True, # HttpOnly cookie flag
    frame_options='DENY', # Prevent framing
    content_security_policy_nonce_in=['script-src'] # If you need inline scripts later
)


# --- Helper Function for Template Context ---
def get_context():
    """Returns common context variables for templates."""
    return {
        'PQC_ENABLED': PQC_ENABLED,
        'PQC_LIBRARY_NAME': PQC_LIBRARY_NAME,
        'KEM_ALGORITHM': KEM_ALGORITHM,
        'public_key': session.get('public_key_hex'),
        'private_key': session.get('private_key_hex'),
        'ciphertext': session.get('ciphertext_hex'),
        'shared_secret_original': session.get('shared_secret_original_hex'),
        'shared_secret_recovered': session.get('shared_secret_recovered_hex'),
    }

# --- Routes ---

@app.route('/')
def index():
    return render_template('index.html', **get_context())

@app.route('/generate-keys', methods=['POST'])
def generate_keys():
    if not PQC_ENABLED or kem_generate_keypair is None:
        flash(f'PQC Library ({PQC_LIBRARY_NAME}) or KEM ({KEM_ALGORITHM}) not available. Key generation disabled.', 'error')
        return redirect(url_for('index'))

    try:
        public_key_bytes, private_key_bytes = kem_generate_keypair()

        # Store keys in session (convert to hex for JSON serializability)
        session['public_key_hex'] = public_key_bytes.hex()
        session['private_key_hex'] = private_key_bytes.hex()
        # Clear previous results when new keys are generated
        session.pop('ciphertext_hex', None)
        session.pop('shared_secret_original_hex', None)
        session.pop('shared_secret_recovered_hex', None)

        flash(f'Successfully generated keys using {KEM_ALGORITHM}.', 'success')
        return redirect(url_for('index')) # Redirect to show results via session
    except Exception as e:
        flash(f'An unexpected error occurred during key generation: {e}', 'error')
        print(f"Unexpected PQC Key Generation Error ({KEM_ALGORITHM}): {e}")
        traceback.print_exc()
        return redirect(url_for('index'))


@app.route('/encrypt', methods=['POST'])
def encrypt_message(): # Renamed endpoint for clarity, matches form action
    if not PQC_ENABLED or kem_encrypt is None:
        flash(f'PQC Library ({PQC_LIBRARY_NAME}) or KEM ({KEM_ALGORITHM}) not available. Encapsulation disabled.', 'error')
        return redirect(url_for('index'))

    public_key_hex = request.form.get('public_key', '').strip()

    if not public_key_hex:
        flash('Public key is required for encapsulation.', 'error')
        return redirect(url_for('index'))

    try:
        public_key_bytes = bytes.fromhex(public_key_hex)
    except ValueError:
        flash('Invalid Public Key format (must be hex).', 'error')
        return redirect(url_for('index'))

    try:
        # Call the specific imported encrypt function (KEM Encapsulation)
        ciphertext_bytes, plaintext_original_bytes = kem_encrypt(public_key_bytes)

        # Store results in session
        session['ciphertext_hex'] = ciphertext_bytes.hex()
        session['shared_secret_original_hex'] = plaintext_original_bytes.hex()
        session.pop('shared_secret_recovered_hex', None) # Clear recovered secret

        flash(f'Encapsulation successful using {KEM_ALGORITHM}. Ciphertext generated.', 'success')
        # Don't flash the secret, display it via template context for demo purposes
        # flash(f'Original Plaintext Secret (hex, normally kept secret): {plaintext_original_bytes.hex()}', 'info')

        return redirect(url_for('index')) # Redirect to show results
    except ValueError as ve: # Catch specific errors like incorrect key size for the algorithm
         flash(f'PQC Value Error during encapsulation (likely incorrect public key for {KEM_ALGORITHM}): {ve}', 'error')
         print(f"Value Error ({KEM_ALGORITHM}): {ve}")
         # No traceback for value errors unless debugging
         return redirect(url_for('index'))
    except Exception as e:
        flash(f'An unexpected error occurred during PQC encapsulation: {e}', 'error')
        print(f"Unexpected PQC Encapsulation Error ({KEM_ALGORITHM}): {e}")
        traceback.print_exc()
        return redirect(url_for('index'))


@app.route('/decrypt', methods=['POST'])
def decrypt_message(): # Renamed endpoint for clarity, matches form action
    if not PQC_ENABLED or kem_decrypt is None:
        flash(f'PQC Library ({PQC_LIBRARY_NAME}) or KEM ({KEM_ALGORITHM}) not available. Decapsulation disabled.', 'error')
        return redirect(url_for('index'))

    private_key_hex = request.form.get('private_key', '').strip()
    ciphertext_hex = request.form.get('ciphertext', '').strip()

    if not private_key_hex or not ciphertext_hex:
        flash('Private key and ciphertext are required for decapsulation.', 'error')
        return redirect(url_for('index'))

    try:
        private_key_bytes = bytes.fromhex(private_key_hex)
        ciphertext_bytes = bytes.fromhex(ciphertext_hex)
    except ValueError:
        flash('Invalid Private Key or Ciphertext format (must be hex).', 'error')
        return redirect(url_for('index'))

    try:
        # Call the specific imported decrypt function (KEM Decapsulation)
        plaintext_recovered_bytes = kem_decrypt(private_key_bytes, ciphertext_bytes)

        session['shared_secret_recovered_hex'] = plaintext_recovered_bytes.hex()
        flash('Decapsulation successful.', 'success')

        # Optionally compare recovered with original if it exists in session
        original_secret_hex = session.get('shared_secret_original_hex')
        if original_secret_hex and original_secret_hex == plaintext_recovered_bytes.hex():
             flash('Recovered secret matches the original encapsulated secret.', 'info')
        elif original_secret_hex:
             flash('Warning: Recovered secret does NOT match the original encapsulated secret!', 'error')


        return redirect(url_for('index')) # Redirect to show results
    except ValueError as ve: # Catch specific errors like incorrect key/ciphertext size or decapsulation failure
         flash(f'PQC Value Error during decapsulation (incorrect private key, corrupted ciphertext, or decapsulation failure for {KEM_ALGORITHM}?): {ve}', 'error')
         print(f"Value Error ({KEM_ALGORITHM}) during decapsulation: {ve}")
         # No traceback for value errors unless debugging
         return redirect(url_for('index'))
    except Exception as e: # Catch other potential errors
        flash(f'An unexpected error occurred during PQC decapsulation: {e}', 'error')
        print(f"Unexpected PQC Decapsulation Error ({KEM_ALGORITHM}): {e}")
        traceback.print_exc()
        return redirect(url_for('index'))


# --- Error Handling ---
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    print(f"Internal Server Error: {e}")
    traceback.print_exc() # Log the full error
    # Don't flash here, render the 500 page directly
    return render_template('500.html'), 500

# Add a route to clear the session data for easy resetting
@app.route('/clear', methods=['POST'])
def clear_session():
    session.clear()
    flash('Session data cleared.', 'info')
    return redirect(url_for('index'))


if __name__ == '__main__':
    host = '127.0.0.1'
    port = 5000
    # Debug mode based on FLASK_ENV=development, default is False (production)
    debug = os.environ.get('FLASK_ENV', 'production').lower() == 'development'
    print(f"Starting Flask app in {os.environ.get('FLASK_ENV', 'production')} mode.")
    print(f" * Running on http://{host}:{port}/")
    print(f" * Debug mode: {'on' if debug else 'off'}")
    if not PQC_ENABLED:
        print(f" * WARNING: PQC functionality for {KEM_ALGORITHM} is disabled due to import errors.")
    app.run(host=host, port=port, debug=debug)

