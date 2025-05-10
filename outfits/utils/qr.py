import qrcode
import io
import base64

def _format_recipient(recipient: str) -> str:
    """Convert Thai mobile number to PromptPay format (0066XXXXXXXXX)."""
    recipient = recipient.strip().replace("-", "")
    if recipient.startswith("0") and len(recipient) == 10:
        return "0066" + recipient[1:]  # remove first 0 and add country code
    raise ValueError("Invalid Thai mobile number format")

def _crc16(data: bytes) -> str:
    """Calculate CRC16 checksum (XMODEM) for PromptPay QR payload."""
    crc = 0xFFFF
    for b in data:
        crc ^= b << 8
        for _ in range(8):
            crc = (crc << 1) ^ 0x1021 if (crc & 0x8000) else crc << 1
            crc &= 0xFFFF
    return format(crc, '04X')

def _generate_payload(recipient: str, amount: float = None) -> str:
    """
    Generate PromptPay payload with optional fixed amount.
    Spec: https://www.bot.or.th/English/PaymentSystems/PromptPay
    """
    recipient = _format_recipient(recipient)

    payload = "000201"  # Payload Format Indicator
    payload += "010212"  # Point of Initiation Method (12 = dynamic)

    # Merchant Account Info - PromptPay
    guid = "A000000677010111"
    acc_info = f"0016{guid}0213{recipient}"
    payload += f"29{len(acc_info):02d}{acc_info}"

    if amount is not None:
        amt_str = f"{amount:.2f}"
        payload += f"54{len(amt_str):02d}{amt_str}"

    payload += "5802TH"  # Country Code
    payload += "6304"    # CRC placeholder
    crc = _crc16(payload.encode("ascii"))
    return payload + crc

def generate_promptpay_qr(recipient: str, amount: float = None) -> str:
    payload = _generate_payload(recipient, amount)
    qr = qrcode.make(payload)
    buffered = io.BytesIO()
    qr.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode("utf-8")
