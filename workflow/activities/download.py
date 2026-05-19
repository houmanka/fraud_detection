from dataclasses import dataclass

from temporalio import activity

@dataclass
class FileDetails:
    path: str
    provider: str # need to change it to be the cloud client


@activity.defn
def download_activity(arg: FileDetails) -> str:
    # donwload
    return f"{arg.provider}:{arg.path}"