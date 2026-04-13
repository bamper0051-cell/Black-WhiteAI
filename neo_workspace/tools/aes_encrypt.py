from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import os
import base64
import zipfile
import secrets

def run_tool(inputs: dict) -> dict:
    output_dir = inputs.get("output_dir", "/tmp")
    try:
        # Generate a random 256-bit key for AES encryption
        key = secrets.token_bytes(32)
        
        # Generate a random 128-bit initialization vector (IV) for AES encryption
        iv = secrets.token_bytes(16)
        
        # Get the content to be encrypted
        content = inputs.get("content", "").encode("utf-8")
        
        # Create a new AES cipher object with the generated key and IV
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
        encryptor = cipher.encryptor()
        
        # Pad the content to the nearest multiple of the block size (16 bytes for AES)
        padder = padding.PKCS7(128).padder()
        padded_content = padder.update(content) + padder.finalize()
        
        # Encrypt the padded content
        encrypted_content = encryptor.update(padded_content) + encryptor.finalize()
        
        # Save the encrypted content to a file
        encrypted_file_path = os.path.join(output_dir, "encrypted.txt")
        with open(encrypted_file_path, "wb") as f:
            f.write(encrypted_content)
        
        # Save the key and IV to a file
        key_file_path = os.path.join(output_dir, "key.txt")
        with open(key_file_path, "wb") as f:
            f.write(key + iv)
        
        # Create a ZIP archive containing the encrypted file and key
        zip_file_path = os.path.join(output_dir, "encrypted.zip")
        with zipfile.ZipFile(zip_file_path, "w") as zip_file:
            zip_file.write(encrypted_file_path, "encrypted.txt")
            zip_file.write(key_file_path, "key.txt")
        
        # Print progress
        print("Encrypted content saved to", encrypted_file_path)
        print("Key and IV saved to", key_file_path)
        print("ZIP archive created at", zip_file_path)
        
        # Return the result
        result = "Encrypted content and key saved to ZIP archive at " + zip_file_path
        return {"ok": True, "output": result, "files": [zip_file_path], "error": ""}
    except Exception as e:
        return {"ok": False, "output": "", "files": [], "error": str(e)}