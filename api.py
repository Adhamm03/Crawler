from fastapi import FastAPI
from pydantic import BaseModel
from fetchSite import get_company_info

app = FastAPI(title="Company Info Crawler API")


class CompanyRequest(BaseModel):
    company: str
    country: str


@app.post("/company-info")
def company_info(req: CompanyRequest):
    return get_company_info(req.company, req.country)


@app.get("/health")
def health():
    return {"status": "ok"}
