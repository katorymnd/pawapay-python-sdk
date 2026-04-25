# PawaPay Python SDK (Premium)

A secure, high-performance Python implementation for PawaPay integration, featuring a powered core and native bytecode validation for industrial-grade security.

**Purchase License:** [katorymnd.com/pawapay-payment-sdk/python](https://katorymnd.com/pawapay-payment-sdk/python)

---

## 🛠 Installation Guide (Ubuntu Server)

### 1. Prepare the Environment
Ensure your server has the necessary Python components:
```bash
sudo apt update
sudo apt install python3-venv python3-pip -y
```

### 2. Setup the Workspace
Navigate to your project directory and create an isolated environment:
```bash
cd /path/to/your/project
python3 -m venv .venv
source .venv/bin/activate
pip install fastapi uvicorn
```

### 3. Install the SDK and setup
Upload your `.whl` file to the server and install:
```bash
pip install katorymnd-pawapay-python-sdk 
katorymnd-pawapay-setup # initialize sdk setup
```

---

## ⚙️ Configuration

Create a `.env` file in your root directory:
```env
# .env
PAWAPAY_SANDBOX_API_TOKEN=your_token_here
PAWAPAY_PRODUCTION_API_TOKEN=your_production_api_token_here
KATORYMND_PAWAPAY_SDK_LICENSE_KEY=your_key_here
PAWAPAY_SDK_LICENSE_DOMAIN=your_domain_here
PAWAPAY_SDK_LICENSE_SECRET=your_key_here

```

---

## 🚀 Surgical Usage Examples

### 1. Initiate a Deposit (V2)
```python
from src.api.ApiClient import ApiClient
from src.utils.helpers import Helpers

config = {
    'api_token': 'YOUR_TOKEN',
    'environment': 'sandbox',
    'api_version': 'v2',
    'license_key': 'YOUR_LICENSE'
}

client = ApiClient(config)
response = await client.initiate_deposit_v2(
    deposit_id=Helpers.generate_unique_id(),
    amount="5000",
    currency="UGX",
    payer_msisdn="256783456789",
    provider="MTN_MOMO_UGA",
    customer_message="Payment for Order #1"
)
```
**Expected Response:**
```json
{
  "depositId": "c6010b6c-871a-4d36-9bfc-b9a0f5f8b226",
  "status": "ACCEPTED",
  "created": "2026-04-25T11:24:41Z",
  "nextStep": "FINAL_STATUS"
}
```

### 2. Create a Payment Page (V2)
```python
params = {
    'depositId': Helpers.generate_unique_id(),
    'amount': "5000",
    'currency': "UGX",
    'returnUrl': "https://yourdomain.com/success",
    'customerMessage': "SDK Test",
    'country': "UGA",
    'phoneNumber': "256783456789"
}
response = await client.create_payment_page_session_v2(params)
```
**Expected Response:**
```json
{
  "status": 201,
  "response": {
    "depositId": "31c56b59-d17f-...",
    "redirectUrl": "https://sandbox.paywith.pawapay.io/v2?token=..."
  }
}
```

### 3. Initiate a Payout (V2)
```python
response = await client.initiate_payout_v2(
    payout_id=Helpers.generate_unique_id(),
    amount="5000",
    currency="UGX",
    recipient_msisdn="256783456789",
    provider="MTN_MOMO_UGA",
    customer_message="Monthly Salary"
)
```
**Expected Response:**
```json
{
  "payoutId": "1aacbb3b-c0ef-4c05-a0f9-eb8c47e0c34a",
  "status": "ACCEPTED",
  "created": "2026-04-25T12:17:41Z"
}
```

---

## 🔍 Transaction Management

### Check Status (CLI)
The SDK includes a surgical status checker. Replace `<UUID>` with your transaction ID:
```bash
# Check a Deposit
python test_transaction_status.py <UUID> -t deposit -v v2

# Check a Payout
python test_transaction_status.py <UUID> -t payout -v v2
```

**Successful Status Response:**
```json
{
  "data": {
    "status": "COMPLETED",
    "amount": "5000.00",
    "currency": "UGX",
    "providerTransactionId": "eeeaa10f-b453-4db3-bb59-df668a066c31"
  },
  "status": "FOUND"
}
```

---

## 🛡 Security & Persistence

### Background Service
To keep your SDK server running permanently on Ubuntu, create a service file:
`/etc/systemd/system/pawapay-python.service`

```ini
[Service]
WorkingDirectory=/path/to/your/project
Environment="PATH=/path/to/your/project/.venv/bin"
ExecStart=/path/to/your/project/.venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000
Restart=always
```

### Integrity Protection
This SDK utilizes a **Native Core Loader**. Upon initialization (`katorymnd-pawapay-setup`):
* **.pawapay-imprint**: Anchors the SDK to your specific server environment.
* **Bytecode VM**: Executes transaction logic via randomized opcodes to prevent tampering.

---

**Support:** For integration help or license issues, visit [katorymnd.com Support](https://katorymnd.com).