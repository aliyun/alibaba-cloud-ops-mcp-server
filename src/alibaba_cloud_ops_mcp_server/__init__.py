from . import server
import asyncio
import logging

logging.getLogger().setLevel(logging.INFO)

def main():
    """Main entry point for the package."""
    asyncio.run(server.main())

__all__ = ['main', 'server']
