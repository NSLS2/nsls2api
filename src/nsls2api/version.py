import importlib.metadata


def get_version() -> str:
    """Get the version of the nsls2api package"""
    try:
        return importlib.metadata.version("nsls2api")
    except importlib.metadata.PackageNotFoundError:
        return "unknown"
