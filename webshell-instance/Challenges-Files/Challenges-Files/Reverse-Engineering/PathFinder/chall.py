import os
import sys
import time

def challenge():
    # -------------------------------------------------------------
    # CONFIGURATION
    # -------------------------------------------------------------
    # XOR Key: 66
    payload = [
        48, 49, 55, 1, 22, 4, 57, 33, 114, 38, 113, 29, 
        50, 114, 46, 59, 37, 46, 114, 117, 63
    ]
    key = 66
    target_dir = "message.txt"

    required_structure = os.path.join("n", "u", "l", "l", "b", "y", "t", "e", "z")

    # -------------------------------------------------------------
    # ENVIRONMENT CHECKS
    # -------------------------------------------------------------
    print(f"[SYSTEM] Host OS: {sys.platform}")
    print("[SYSTEM] Verifying coordinates...")
    time.sleep(1)

    current_path = os.getcwd()

    if not current_path.endswith(required_structure):
        print("\n[ACCESS DENIED]")
        return

    if not os.path.exists(target_dir):
        print(f"\n[WARNING] Authentication missing.")
        return

    # -------------------------------------------------------------
    # DECRYPTION
    # -------------------------------------------------------------
    print("\n[SUCCESS] Environment confirmed. Decrypting...")
    
    decrypted_chars = [chr(x ^ key) for x in payload]
    flag = "".join(decrypted_chars)

    print("------------------------------------------------")
    print("Message: Polyglot code executed successfully.")
    print(f"Flag:    {flag}")
    print("------------------------------------------------")

    try:
        with open(target_dir, "w") as f:
            f.write(f"Flag: {flag}")
            print(f"[SYSTEM] Flag written to {target_dir}")
    except:
        print("[ERROR] Could not write to file.")

if __name__ == "__main__":
    challenge()
