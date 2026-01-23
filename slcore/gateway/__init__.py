def __getattr__(name: str):
    """Lazy import to avoid MADSci argument parser interference."""
    if name in ("RestGateway", "run_gateway"):
        from slcore.gateway.rest_gateway import RestGateway, run_gateway
        return {"RestGateway": RestGateway, "run_gateway": run_gateway}[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["RestGateway", "run_gateway"]
