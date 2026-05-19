from presidio_analyzer import AnalyzerEngine
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("PII_CLASSIFY")
analyzer = AnalyzerEngine()

@mcp.tool()
async def pii_classify(comma_delimited_string: str) -> dict:
    results = analyzer.analyze(text=comma_delimited_string, language='en')
    if results:
        print("PII detected:")
        entities = []
        for result in results:
            entities.append({
                "start": result.start,
                "end": result.end,
                "score": result.score,
                "entity": result.entity_type,
            })

        return {"status":"Sensitive","entities":entities}
    else:
        return {"status":"Non-Sensitive","entities":[]}


def main():
    mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()