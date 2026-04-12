import json

class AuthModule:
    def __init__(self):
        self.pin_auth_enabled = True
        self.captcha_enabled = True
        self.username_password_auth_enabled = True

    def login_with_pin(self, pin):
        # Validate the provided PIN
        if self.validate_pin(pin):
            return "Authenticated with PIN!"
        else:
            return "Invalid PIN"

    def login_with_captcha(self, captcha_response):
        # Validate the CAPTCHA response
        if self.validate_captcha(captcha_response):
            return "Authenticated with CAPTCHA!"
        else:
            return "Invalid CAPTCHA"

    def login_with_username_password(self, username, password):
        # Validate the provided username and password
        if self.validate_credentials(username, password):
            return "Authenticated with Username and Password!"
        else:
            return "Invalid username or password"

    def validate_pin(self, pin):
        # Placeholder for PIN validation logic
        return pin == "1234"

    def validate_captcha(self, captcha_response):
        # Placeholder for CAPTCHA validation logic
        return captcha_response == "valid_captcha"

    def validate_credentials(self, username, password):
        # Placeholder for username and password validation logic, using a hardcoded example
        return (username == "admin" and password == "pass")

# Example usage:
if __name__ == '__main__':
    auth = AuthModule()
    print(auth.login_with_pin("1234"))
    print(auth.login_with_captcha("valid_captcha"))
    print(auth.login_with_username_password("admin", "pass"))
