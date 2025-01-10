search_case = dict(
    name="search_case",
    description="Search for cases related to the question asked by the user",
    parameters={
        "type": "OBJECT",
        "properties": {
            "querystring": {
                "type": "STRING",
                "description": "The search string to use to find cases",
            },
            "from_date": {
                "type": "STRING",
                "description": "Start date to search for cases"
            },
        },
    },
)