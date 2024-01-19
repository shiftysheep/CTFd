import logging
import tempfile
import traceback
from typing import Optional

import requests
from flask import Request, request

from ..models.models import DockerConfig

logger = logging.getLogger(__name__)


def do_request(
    docker: DockerConfig,
    url: str,
    method: str = "GET",
    headers: Optional[dict] = None,
    data: Optional[dict] = None,
) -> requests.Response:
    tls = docker.tls_enabled
    prefix = "https" if tls else "http"
    host = docker.hostname
    BASE_URL = f"{prefix}://{host}"
    if not headers:
        headers = {"Content-Type": "application/json"}
    if tls:
        if method == "DELETE":
            r = requests.delete(
                url=f"{BASE_URL}{url}",
                cert=(docker.client_cert, docker.client_key),
                verify=docker.ca_cert,
                headers=headers,
            )
        elif method == "GET":
            r = requests.get(
                url=f"{BASE_URL}{url}",
                cert=(docker.client_cert, docker.client_key),
                verify=docker.ca_cert,
                headers=headers,
            )
        elif method == "POST":
            r = requests.post(
                url=f"{BASE_URL}{url}",
                cert=(docker.client_cert, docker.client_key),
                verify=docker.ca_cert,
                headers=headers,
                data=data,
            )
    elif method == "DELETE":
        r = requests.delete(url=f"{BASE_URL}{url}", headers=headers)
    elif method == "GET":
        r = requests.get(url=f"{BASE_URL}{url}", headers=headers)
    elif method == "POST":
        r = requests.post(url=f"{BASE_URL}{url}", headers=headers, data=data)
    return r


# For the Docker Config Page. Gets the Current Repositories available on the Docker Server.
def get_repositories(
    docker: DockerConfig, tags: bool = False, repos: bool = False
) -> list:
    r = do_request(docker, "/images/json?all=1")
    result = []
    for i in r.json():
        if i["RepoTags"] is not None and i["RepoTags"][0].split(":")[0] != "<none>":
            if repos and i["RepoTags"][0].split(":")[0] not in repos:
                continue
            if not tags:
                result.append(i["RepoTags"][0].split(":")[0])
            else:
                result.append(i["RepoTags"][0])
    return list(set(result))


def get_secrets(docker):
    r = do_request(docker, "/secrets")
    tmplist = []
    for secret in r.json():
        tmpdict = {"ID": secret["ID"], "Name": secret["Spec"]["Name"]}
        tmplist.append(tmpdict)
    return tmplist


def delete_secret(docker: DockerConfig, id: str):
    r = do_request(docker, f"/secrets/{id}", method="DELETE")
    return r.ok


def get_unavailable_ports(docker):
    r = do_request(docker, "/containers/json?all=1")
    result = []
    for i in r.json():
        if i["Ports"] != []:
            result.extend(p["PublicPort"] for p in i["Ports"] if p.get("PublicPort"))
    r = do_request(docker, "/services?all=1")
    for i in r.json():
        endpoint = i["Endpoint"]["Spec"]
        if endpoint != {}:
            result.extend(
                p["PublishedPort"] for p in endpoint["Ports"] if p.get("PublishedPort")
            )
    return result


def get_required_ports(docker, image):
    r = do_request(docker, f"/images/{image}/json?all=1")
    return r.json()["Config"]["ExposedPorts"].keys()


def create_temp_file(in_file: bytes) -> str:
    """Create temp file and  return temp name."""
    temp_file = tempfile.NamedTemporaryFile(mode="wb", dir="/tmp", delete=False)
    temp_file.write(in_file)
    temp_file.seek(0)
    return temp_file.name


def get_file(request: Request, file_name: str) -> bytes:
    contents = request.files.get(file_name)
    return contents.stream.read() if contents else b""
