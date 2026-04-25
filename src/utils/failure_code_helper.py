# src/utils/failure_code_helper.py
"""
Failure Code Helper
Maps and explains PawaPay error codes
"""


class FailureCodeHelper: 
    """
    Helper class for mapping and explaining PawaPay error codes
    """
    
    # Aliases to normalize code names across V1/V2 and operations.
    aliases = {
        # Provider/Correspondent synonyms
        'CORRESPONDENT_TEMPORARILY_UNAVAILABLE': 'PROVIDER_TEMPORARILY_UNAVAILABLE',
        # Amount bounds synonyms
        'AMOUNT_TOO_SMALL': 'AMOUNT_OUT_OF_BOUNDS',
        'AMOUNT_TOO_LARGE': 'AMOUNT_OUT_OF_BOUNDS',
        # Phone number / format synonyms
        'INVALID_RECIPIENT_FORMAT': 'INVALID_PHONE_NUMBER',
        'INVALID_PAYER_FORMAT': 'INVALID_PHONE_NUMBER',
        # Balance synonyms
        'BALANCE_INSUFFICIENT': 'PAWAPAY_WALLET_OUT_OF_FUNDS',
        # Flow synonyms (already-in-process)
        'TRANSACTION_ALREADY_IN_PROCESS': 'PAYMENT_IN_PROGRESS',
        # Recipient allowed / wallet limits
        'RECIPIENT_NOT_ALLOWED_TO_RECEIVE': 'WALLET_LIMIT_REACHED',
        # "Not found" mapping across ops
        'DEPOSIT_NOT_FOUND': 'NOT_FOUND',
        # Generic other error
        'OTHER_ERROR': 'UNKNOWN_ERROR'
    }
    
    # Rejection messages (initiation time) — V1 + V2
    rejection_messages = {
        # Common transport/auth/signature (V2)
        'NO_AUTHENTICATION': 'Authentication header is missing.',
        'AUTHENTICATION_ERROR': 'The API token is invalid.',
        'AUTHORISATION_ERROR': 'The API token is not authorised for this request.',
        'HTTP_SIGNATURE_ERROR': 'The HTTP signature failed verification.',
        'INVALID_INPUT': 'We could not parse the request payload.',
        'MISSING_PARAMETER': 'A required parameter is missing.',
        'UNSUPPORTED_PARAMETER': 'An unsupported parameter was provided.',
        'INVALID_PARAMETER': 'A parameter contains an invalid value.',
        'DUPLICATE_METADATA_FIELD': 'Duplicate field in metadata.',
        # Amount/currency/provider/country
        'INVALID_AMOUNT': 'The amount is not valid for this provider.',
        'AMOUNT_OUT_OF_BOUNDS': 'The amount is outside provider limits.',
        'INVALID_CURRENCY': 'The currency is not supported by this provider.',
        'INVALID_COUNTRY': 'The specified country is not supported.',
        'INVALID_PROVIDER': 'The provider is invalid for this request.',
        'INVALID_PHONE_NUMBER': 'The phone number format is invalid.',
        # Business enablement
        'DEPOSITS_NOT_ALLOWED': 'Deposits are not enabled for this provider on your account.',
        'PAYOUTS_NOT_ALLOWED': 'Payouts are not enabled for this provider on your account.',
        'REFUNDS_NOT_ALLOWED': 'Refunds are not enabled for this provider on your account.',
        'REMITTANCES_NOT_ALLOWED': 'Remittances are not enabled for this provider on your account.',
        # Availability
        'PROVIDER_TEMPORARILY_UNAVAILABLE': 'The provider is temporarily unavailable. Please try again later.',
        # V1-only names (aliased above, but keep messages for clarity)
        'INVALID_PAYER_FORMAT': 'The payer phone number format is invalid.',
        'INVALID_RECIPIENT_FORMAT': 'The recipient phone number format is invalid.',
        'INVALID_CORRESPONDENT': 'The specified correspondent is not supported.',
        'AMOUNT_TOO_SMALL': 'The amount is below the minimum.',
        'AMOUNT_TOO_LARGE': 'The amount is above the maximum.',
        'CORRESPONDENT_TEMPORARILY_UNAVAILABLE': 'The MMO (correspondent) is temporarily unavailable.',
        # Refund-specific V1
        'DEPOSIT_NOT_COMPLETED': 'The referenced deposit was not completed.',
        'ALREADY_REFUNDED': 'The referenced deposit has already been refunded.',
        'IN_PROGRESS': 'Another refund transaction is already in progress.',
        'DEPOSIT_NOT_FOUND': 'The referenced deposit was not found.',
        # Refund-specific V2
        'NOT_FOUND': 'The referenced deposit was not found.',
        'INVALID_STATE': 'The deposit is not in a refundable state (or already refunded).',
        # Wallet balance (initiation level)
        'PAWAPAY_WALLET_OUT_OF_FUNDS': 'Your pawaPay wallet does not have sufficient funds.',
        # Generic
        'UNKNOWN_ERROR': 'An unknown error occurred while processing the request.'
    }
    
    # Failure messages (processing-time) — V1 + V2 + Remittances
    failure_messages = {
        # Deposits (V1 & V2)
        'PAYER_NOT_FOUND': 'The phone number does not belong to the specified provider.',
        'PAYMENT_NOT_APPROVED': 'The customer did not approve the payment.',
        'PAYER_LIMIT_REACHED': 'The customer has reached a wallet transaction limit.',
        'PAYMENT_IN_PROGRESS': 'The customer already has a payment pending.',
        'INSUFFICIENT_BALANCE': 'The customer does not have enough funds.',
        'UNSPECIFIED_FAILURE': 'The provider reported a failure without a reason.',
        'UNKNOWN_ERROR': 'An unknown error occurred.',
        # V1 alias kept for backward compat
        'TRANSACTION_ALREADY_IN_PROCESS': 'A previous transaction is still being processed.',
        # Payouts (V1 & V2)
        'PAWAPAY_WALLET_OUT_OF_FUNDS': 'Your pawaPay wallet does not have sufficient funds.',
        'BALANCE_INSUFFICIENT': 'Your pawaPay wallet does not have sufficient funds.',
        'RECIPIENT_NOT_FOUND': 'The phone number does not belong to the specified provider.',
        'RECIPIENT_NOT_ALLOWED_TO_RECEIVE': 'The recipient is temporarily not allowed to receive funds.',
        'MANUALLY_CANCELLED': 'The payout was cancelled while in queue.',
        # Remittances (V2 naming)
        'WALLET_LIMIT_REACHED': 'The recipient has reached a wallet limit.',
        # Friendly fallbacks
        'OTHER_ERROR': 'An unspecified error occurred while processing the transaction.',
        # Non-standard but used in your app
        'NO_CALLBACK': 'The transaction is pending. Please check the status again shortly.'
    }
    
    # Status messages & terminality — V1 + V2
    status_messages = {
        'ACCEPTED': 'Accepted for processing.',
        'ENQUEUED': 'Accepted and queued for later processing.',
        'SUBMITTED': 'Submitted to the provider.',
        'PROCESSING': 'Processing with the provider.',
        'IN_RECONCILIATION': 'Being reconciled to determine final status.',
        'COMPLETED': 'Successfully completed.',
        'FAILED': 'Processed but failed.',
        # V2 "wrapper" statuses for GET /v2/.../{id}
        'FOUND': 'Found.',
        'NOT_FOUND': 'Not found.',
        # Some V1 payloads use these text keys within responses
        'REJECTED': 'Rejected at initiation.',
        'DUPLICATE_IGNORED': 'Duplicate of an already accepted request; ignored.'
    }
    
    final_statuses = {
        'COMPLETED': True,
        'FAILED': True,
        # "FOUND/NOT_FOUND" are wrapper statuses, not payment lifecycle; treat as final for the lookup call.
        'FOUND': True,
        'NOT_FOUND': True
    }
    
    @staticmethod
    def get_failure_message(failure_code: str) -> str:
        """
        Returns a friendly message for a processing failure code.
        
        Args:
            failure_code: The failure code
            
        Returns:
            Friendly error message
        """
        code = FailureCodeHelper.normalize_code(failure_code)
        
        if code in FailureCodeHelper.failure_messages:
            return FailureCodeHelper.failure_messages[code]
        
        # Check in rejections too (some callers may mix)
        if code in FailureCodeHelper.rejection_messages:
            return FailureCodeHelper.rejection_messages[code]
        
        return f"An unknown error occurred (Code: {code}). Please contact support."
    
    @staticmethod
    def get_rejection_message(rejection_code: str) -> str:
        """
        Friendly message for initiation rejection codes.
        
        Args:
            rejection_code: The rejection code
            
        Returns:
            Friendly error message
        """
        code = FailureCodeHelper.normalize_code(rejection_code)
        
        if code in FailureCodeHelper.rejection_messages:
            return FailureCodeHelper.rejection_messages[code]
        
        # Check in failures too (defensive)
        if code in FailureCodeHelper.failure_messages:
            return FailureCodeHelper.failure_messages[code]
        
        return f"Your request was rejected (Code: {code}). Please review the parameters or try again later."
    
    @staticmethod
    def get_status_message(status: str) -> str:
        """
        Friendly message for a lifecycle/status string (ACCEPTED, COMPLETED, FAILED, etc.)
        
        Args:
            status: The status code
            
        Returns:
            Friendly status message
        """
        s = (status or '').upper().strip()
        return FailureCodeHelper.status_messages.get(s, s)
    
    @staticmethod
    def is_final_status(status: str) -> bool:
        """
        Whether a status is terminal (no more state changes expected).
        
        Args:
            status: The status code
            
        Returns:
            True if status is final
        """
        s = (status or '').upper().strip()
        return FailureCodeHelper.final_statuses.get(s, False)
    
    @staticmethod
    def normalize_code(code: str) -> str:
        """
        Normalize incoming code:
        - uppercase/trim
        - alias to canonical if known
        
        Args:
            code: The code to normalize
            
        Returns:
            Normalized code
        """
        c = (code or '').upper().strip()
        return FailureCodeHelper.aliases.get(c, c)