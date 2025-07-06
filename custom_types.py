from pydantic import BaseModel

class VariantInfo(BaseModel):
    chromosome: str
    position: int
    rsid: str
    gene: str
    reference: str
    alternate: str
    search_summary: str 