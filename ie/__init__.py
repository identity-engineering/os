"""IE OS command-line package."""

from importlib.metadata import PackageNotFoundError, version as distribution_version

try:
	from ._version import __version__
except ImportError:
	try:
		__version__ = distribution_version("ie-os")
	except PackageNotFoundError:
		__version__ = "0.0.0.dev0"
