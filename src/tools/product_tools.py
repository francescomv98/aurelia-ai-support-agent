from src.auth.models import AuthenticatedUser
from src.services.product_service import ProductResult, get_product

def get_product_tool(db, product_code: str, user: AuthenticatedUser) -> ProductResult:
    """
    Retrieve product information from the enterprise database.
    """

    return get_product(db=db, product_code=product_code)