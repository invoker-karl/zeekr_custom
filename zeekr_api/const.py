"""Constants."""

X_CA_SECRET = "MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQCz09z6e9WOcNq+nUMX8Vq1Xe2EmJxuR3XbtureDCS90dfkok"  # noqa: E501, S105
AES_KEY = "a01a6db985a2f5d4"
AES_IV = "ed446b8b8845013d"
APP_SECRET = "890efe3207af95348b95f66b2ee7da04"  # noqa: S105
SECRET_KEY = "e83a60805fa54de9bdfcb0f2d6bca757"  # noqa: S105

TO_BE_SIGNED_HEADER = [
    "x-app-id",
    "content-type",
    "x-api-signature-nonce",
    "x-timestamp",
    "x-api-signature-version",
    "x-project-id",
    "authorization",
    "accept-language",
    "x-vin",
    "x-device-id",
    "x-platform",
]
