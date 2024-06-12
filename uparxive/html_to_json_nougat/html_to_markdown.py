from ..batch_run_utils import BatchModeConfig, dataclass
from .nougat.dataset.parser.latexml_parser import parse_latexml

@dataclass
class HTMLtoMDConfig(BatchModeConfig):
    task_name = 'html_to_md'

