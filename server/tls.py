import os
import ssl

import certifi


def create_ssl_context() -> ssl.SSLContext:
    context = ssl.create_default_context()
    context.load_verify_locations(cafile=certifi.where())
    ca_bundle = os.getenv("CJCHATBOT_CA_BUNDLE")
    if ca_bundle:
        context.load_verify_locations(cafile=ca_bundle)
    return context
