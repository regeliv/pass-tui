import app

def passstore_exists():
    return True

def decrypt():
    print("Decrypting")

def open_pass_store():
    decrypt()
    pass

def create_pass_store():
    pass

def load_theme():
    print("Loading autumn theme")

def start_ui():
    load_theme()
    pass_app = app.Pass()
    pass_app.run()

def read_config():
    # finds pass store if it exists
    # reads config file if it exists
    print("Finding passstore")
    print("Reading user config")

if __name__ == "__main__":
    read_config()
    start_ui()
    if passstore_exists():
        open_pass_store()
    else:
        create_pass_store()

    




