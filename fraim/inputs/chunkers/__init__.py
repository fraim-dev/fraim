from abc import abstractmethod

from fraim.inputs.chunkers.file import FileChunker
from fraim.inputs.chunkers.fixed import FixedCharChunker, FixedTokenChunker
from fraim.inputs.chunkers.max_context import MaxContextChunker
