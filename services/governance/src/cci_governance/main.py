import uvicorn

from .api import app
from .config import GovernanceSettings

if __name__ == "__main__":
    s = GovernanceSettings()
    uvicorn.run(app, host="0.0.0.0", port=s.CCI_GOVERNANCE_PORT, log_level="info")
