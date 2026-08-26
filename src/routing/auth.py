from src.models.meta import Meta, Query, Result
from src.models.either import Right
from src.models.pipe import Pipe


def Wrap(query: Query) -> Pipe:
    meta_info: Meta = Meta(query)
    result: Result = Right(meta_info)
    return Pipe(result)
