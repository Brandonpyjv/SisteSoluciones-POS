from fastapi import APIRouter, Request
from services.product_discount_service import get_all_product_discounts
from templates_config import templates

router = APIRouter()


@router.get("/product_discounts", name="product_discounts")
def product_discounts(request: Request):
    data = get_all_product_discounts()
    return templates.TemplateResponse(request, "product_discounts/index.html", {"all_product_discounts": data})


@router.get("/new_product_discounts", name="new_product_discounts")
def new_product_discounts(request: Request):
    return templates.TemplateResponse(request, "product_discounts/form.html")
