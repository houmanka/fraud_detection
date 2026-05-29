from dataclasses import dataclass

from temporalio import activity

from cloud_storage.contract import CloudStorage


@dataclass
class FileDetails:
    path: str
    provider: str # need to change it to be the cloud client

""" TODO: IMPLEMENT
    Stream file
    For each row:
        MCP pii_classify
        sanitize/redact
        classify with your ML model
        write result to the the postgres 
"""


class DownloadActivities:
    def __init__(self, cloud_storage: CloudStorage):
        self.cloud_storage = cloud_storage

    @activity.defn
    def download_activity(self, arg: FileDetails) -> str:

        itr = self.cloud_storage.iter_text_lines(bucket=arg.path)

        # loop over each line
        for line in itr:


        return f"{arg.provider}:{arg.path}"




