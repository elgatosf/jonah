from .jonah import Deployer
try:
    import jonah.version
except ImportError:
    # Python 2 compatibility
    import version
