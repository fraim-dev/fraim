# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""
IaC Port Extractor

Extracts actual port mappings from Infrastructure as Code files rather than 
making assumptions. This provides ground truth about how services are actually configured.
"""

import json
import re
import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass
from enum import Enum


class PortMappingSource(Enum):
    """Source of port mapping information."""
    DOCKER_COMPOSE = "docker_compose"
    KUBERNETES_MANIFEST = "kubernetes_manifest"
    DOCKERFILE = "dockerfile"
    TERRAFORM = "terraform"
    HELM_CHART = "helm_chart"
    CONFIGURATION_FILE = "configuration_file"
    ENVIRONMENT_VARIABLE = "environment_variable"
    COMMAND_LINE_ARG = "command_line_arg"
    SERVICE_DEFINITION = "service_definition"


@dataclass
class ExtractedPortMapping:
    """A port mapping extracted from IaC files."""
    service_name: str
    container_port: int
    host_port: Optional[int] = None
    protocol: str = "TCP"
    source: PortMappingSource = PortMappingSource.DOCKER_COMPOSE
    source_file: str = ""
    source_line: Optional[int] = None
    context: Optional[Dict[str, Any]] = None
    confidence: float = 1.0  # 1.0 = definitely correct, 0.0 = uncertain


class IaCPortExtractor:
    """Extracts port mappings from Infrastructure as Code files."""

    def __init__(self) -> None:
        self.extracted_mappings: List[ExtractedPortMapping] = []
        self.supported_files = {
            'docker-compose.yml', 'docker-compose.yaml',
            'compose.yml', 'compose.yaml',
            'Dockerfile', 'dockerfile',
            '*.tf', '*.terraform',
            'deployment.yaml', 'deployment.yml',
            'service.yaml', 'service.yml',
            'values.yaml', 'values.yml',
            'Chart.yaml', 'Chart.yml'
        }

    def extract_from_directory(self, directory: Path) -> List[ExtractedPortMapping]:
        """Extract port mappings from all IaC files in a directory."""
        self.extracted_mappings = []

        if not directory.exists():
            return self.extracted_mappings

        # Find all potential IaC files
        iac_files = self._find_iac_files(directory)

        for file_path in iac_files:
            try:
                self._extract_from_file(file_path)
            except Exception as e:
                print(f"Warning: Could not parse {file_path}: {e}")

        return self.extracted_mappings

    def _find_iac_files(self, directory: Path) -> List[Path]:
        """Find all IaC files in directory recursively."""
        iac_files = []

        for file_path in directory.rglob("*"):
            if file_path.is_file():
                if self._is_iac_file(file_path):
                    iac_files.append(file_path)

        return iac_files

    def _is_iac_file(self, file_path: Path) -> bool:
        """Check if a file is an IaC file we can parse."""
        name = file_path.name.lower()

        # Exact matches
        if name in {'docker-compose.yml', 'docker-compose.yaml', 'compose.yml', 'compose.yaml',
                    'dockerfile', 'chart.yaml', 'chart.yml', 'values.yaml', 'values.yml'}:
            return True

        # Pattern matches
        if (name.endswith('.tf') or name.endswith('.terraform') or
            name.endswith('deployment.yaml') or name.endswith('deployment.yml') or
                name.endswith('service.yaml') or name.endswith('service.yml')):
            return True

        return False

    def _extract_from_file(self, file_path: Path) -> None:
        """Extract port mappings from a specific file."""
        name = file_path.name.lower()

        if 'docker-compose' in name or name.startswith('compose'):
            self._extract_from_docker_compose(file_path)
        elif name in {'dockerfile', 'dockerfile.prod', 'dockerfile.dev'}:
            self._extract_from_dockerfile(file_path)
        elif name.endswith('.tf') or name.endswith('.terraform'):
            self._extract_from_terraform(file_path)
        elif 'deployment' in name and name.endswith(('.yaml', '.yml')):
            self._extract_from_k8s_deployment(file_path)
        elif 'service' in name and name.endswith(('.yaml', '.yml')):
            self._extract_from_k8s_service(file_path)
        elif name in {'values.yaml', 'values.yml'}:
            self._extract_from_helm_values(file_path)

    def _extract_from_docker_compose(self, file_path: Path) -> None:
        """Extract port mappings from Docker Compose files."""
        try:
            with open(file_path, 'r') as f:
                compose_data = yaml.safe_load(f)

            services = compose_data.get('services', {})

            for service_name, service_config in services.items():
                if not isinstance(service_config, dict):
                    continue

                # Extract from ports section
                ports = service_config.get('ports', [])
                for port_config in ports:
                    mapping = self._parse_port_mapping(
                        service_name, port_config,
                        PortMappingSource.DOCKER_COMPOSE, str(file_path)
                    )
                    if mapping:
                        self.extracted_mappings.append(mapping)

                # Extract from expose section
                exposed = service_config.get('expose', [])
                for port in exposed:
                    mapping = ExtractedPortMapping(
                        service_name=service_name,
                        container_port=int(port),
                        host_port=None,  # exposed but not mapped to host
                        source=PortMappingSource.DOCKER_COMPOSE,
                        source_file=str(file_path),
                        context={'exposed_only': True}
                    )
                    self.extracted_mappings.append(mapping)

        except Exception as e:
            print(f"Error parsing Docker Compose {file_path}: {e}")

    def _extract_from_dockerfile(self, file_path: Path) -> None:
        """Extract port mappings from Dockerfile EXPOSE instructions."""
        try:
            with open(file_path, 'r') as f:
                content = f.read()

            # Find EXPOSE instructions
            expose_pattern = r'^EXPOSE\s+(.+)$'

            for line_num, line in enumerate(content.split('\n'), 1):
                match = re.match(expose_pattern, line.strip(), re.IGNORECASE)
                if match:
                    ports_str = match.group(1)

                    # Parse port specifications (can be "80", "80/tcp", "80 443", etc.)
                    ports = re.findall(r'(\d+)(?:/(\w+))?', ports_str)

                    for port_num, protocol in ports:
                        mapping = ExtractedPortMapping(
                            service_name=file_path.parent.name,  # Use directory name as service
                            container_port=int(port_num),
                            host_port=None,
                            protocol=protocol.upper() if protocol else "TCP",
                            source=PortMappingSource.DOCKERFILE,
                            source_file=str(file_path),
                            source_line=line_num,
                            confidence=0.8  # EXPOSE doesn't guarantee the service uses this port
                        )
                        self.extracted_mappings.append(mapping)

        except Exception as e:
            print(f"Error parsing Dockerfile {file_path}: {e}")

    def _extract_from_k8s_deployment(self, file_path: Path) -> None:
        """Extract port mappings from Kubernetes deployment manifests."""
        try:
            with open(file_path, 'r') as f:
                docs = yaml.safe_load_all(f)

            for doc in docs:
                if not doc or doc.get('kind') != 'Deployment':
                    continue

                spec = doc.get('spec', {})
                template = spec.get('template', {})
                pod_spec = template.get('spec', {})
                containers = pod_spec.get('containers', [])

                for container in containers:
                    container_name = container.get('name', 'unknown')
                    ports = container.get('ports', [])

                    for port_config in ports:
                        container_port = port_config.get('containerPort')
                        if container_port:
                            mapping = ExtractedPortMapping(
                                service_name=container_name,
                                container_port=int(container_port),
                                host_port=port_config.get('hostPort'),
                                protocol=port_config.get('protocol', 'TCP'),
                                source=PortMappingSource.KUBERNETES_MANIFEST,
                                source_file=str(file_path),
                                context={'port_name': port_config.get('name')}
                            )
                            self.extracted_mappings.append(mapping)

        except Exception as e:
            print(f"Error parsing Kubernetes deployment {file_path}: {e}")

    def _extract_from_k8s_service(self, file_path: Path) -> None:
        """Extract port mappings from Kubernetes service manifests."""
        try:
            with open(file_path, 'r') as f:
                docs = yaml.safe_load_all(f)

            for doc in docs:
                if not doc or doc.get('kind') != 'Service':
                    continue

                metadata = doc.get('metadata', {})
                service_name = metadata.get('name', 'unknown')
                spec = doc.get('spec', {})
                ports = spec.get('ports', [])

                for port_config in ports:
                    port = port_config.get('port')
                    target_port = port_config.get('targetPort', port)

                    if port and str(target_port).isdigit():
                        mapping = ExtractedPortMapping(
                            service_name=service_name,
                            container_port=int(target_port),
                            host_port=int(port),
                            protocol=port_config.get('protocol', 'TCP'),
                            source=PortMappingSource.KUBERNETES_MANIFEST,
                            source_file=str(file_path),
                            context={'service_type': spec.get('type')}
                        )
                        self.extracted_mappings.append(mapping)

        except Exception as e:
            print(f"Error parsing Kubernetes service {file_path}: {e}")

    def _extract_from_terraform(self, file_path: Path) -> None:
        """Extract port mappings from Terraform files."""
        try:
            with open(file_path, 'r') as f:
                content = f.read()

            # Look for port configurations in Terraform resources
            # This is a simplified parser - real Terraform parsing is complex

            # Find port blocks in various resource types
            port_patterns = [
                r'port\s*=\s*(\d+)',
                r'container_port\s*=\s*(\d+)',
                r'host_port\s*=\s*(\d+)',
                r'"(\d+):(\d+)"',  # Docker-style port mapping in strings
            ]

            for pattern in port_patterns:
                matches = re.findall(pattern, content, re.MULTILINE)
                for match in matches:
                    if isinstance(match, tuple):
                        host_port, container_port = match
                        mapping = ExtractedPortMapping(
                            service_name="terraform_service",
                            container_port=int(container_port),
                            host_port=int(host_port),
                            source=PortMappingSource.TERRAFORM,
                            source_file=str(file_path),
                            confidence=0.7  # Terraform parsing is approximate
                        )
                    else:
                        mapping = ExtractedPortMapping(
                            service_name="terraform_service",
                            container_port=int(match),
                            source=PortMappingSource.TERRAFORM,
                            source_file=str(file_path),
                            confidence=0.7
                        )
                    self.extracted_mappings.append(mapping)

        except Exception as e:
            print(f"Error parsing Terraform {file_path}: {e}")

    def _extract_from_helm_values(self, file_path: Path) -> None:
        """Extract port mappings from Helm values files."""
        try:
            with open(file_path, 'r') as f:
                values = yaml.safe_load(f)

            # Common Helm chart patterns for port configuration
            self._extract_helm_ports_recursive(values, str(file_path))

        except Exception as e:
            print(f"Error parsing Helm values {file_path}: {e}")

    def _extract_helm_ports_recursive(self, data: Any, file_path: str, path: str = "") -> None:
        """Recursively extract port configurations from Helm values."""
        if isinstance(data, dict):
            for key, value in data.items():
                current_path = f"{path}.{key}" if path else key

                if key == 'port' and isinstance(value, int):
                    mapping = ExtractedPortMapping(
                        service_name=path.split(
                            '.')[0] if '.' in path else "helm_service",
                        container_port=value,
                        source=PortMappingSource.HELM_CHART,
                        source_file=file_path,
                        context={'helm_path': current_path}
                    )
                    self.extracted_mappings.append(mapping)

                elif key == 'ports' and isinstance(value, list):
                    for port_config in value:
                        if isinstance(port_config, dict):
                            port_num = port_config.get(
                                'port') or port_config.get('containerPort')
                            if port_num:
                                mapping = ExtractedPortMapping(
                                    service_name=path.split(
                                        '.')[0] if '.' in path else "helm_service",
                                    container_port=int(port_num),
                                    host_port=port_config.get('hostPort'),
                                    protocol=port_config.get(
                                        'protocol', 'TCP'),
                                    source=PortMappingSource.HELM_CHART,
                                    source_file=file_path,
                                    context={'helm_path': current_path}
                                )
                                self.extracted_mappings.append(mapping)

                else:
                    self._extract_helm_ports_recursive(
                        value, file_path, current_path)

        elif isinstance(data, list):
            for i, item in enumerate(data):
                self._extract_helm_ports_recursive(
                    item, file_path, f"{path}[{i}]")

    def _parse_port_mapping(self, service_name: str, port_config: Any,
                            source: PortMappingSource, source_file: str) -> Optional[ExtractedPortMapping]:
        """Parse a port configuration from various formats."""
        if isinstance(port_config, int):
            # Simple port number - exposed but not mapped
            return ExtractedPortMapping(
                service_name=service_name,
                container_port=port_config,
                source=source,
                source_file=source_file
            )

        elif isinstance(port_config, str):
            # String format: "8080:80", "8080:80/tcp", "127.0.0.1:8080:80"
            parts = port_config.split(':')
            if len(parts) == 2:
                # "host:container" or "host:container/protocol"
                host_port = int(parts[0])
                container_part = parts[1]

                if '/' in container_part:
                    container_port_str, protocol = container_part.split('/')
                    container_port = int(container_port_str)
                else:
                    container_port = int(container_part)
                    protocol = 'TCP'

                return ExtractedPortMapping(
                    service_name=service_name,
                    container_port=container_port,
                    host_port=host_port,
                    protocol=protocol.upper(),
                    source=source,
                    source_file=source_file
                )

        elif isinstance(port_config, dict):
            # Dict format: {"target": 80, "published": 8080, "protocol": "tcp"}
            container_port_raw = port_config.get(
                'target') or port_config.get('containerPort')
            host_port_raw = port_config.get(
                'published') or port_config.get('hostPort')
            protocol = port_config.get('protocol', 'TCP')

            if container_port_raw:
                return ExtractedPortMapping(
                    service_name=service_name,
                    container_port=int(container_port_raw),
                    host_port=int(host_port_raw) if host_port_raw else None,
                    protocol=protocol.upper(),
                    source=source,
                    source_file=source_file
                )

        return None

    def get_port_mappings_by_service(self) -> Dict[str, List[ExtractedPortMapping]]:
        """Group extracted port mappings by service name."""
        mappings_by_service: Dict[str, List[ExtractedPortMapping]] = {}

        for mapping in self.extracted_mappings:
            service_name = mapping.service_name
            if service_name not in mappings_by_service:
                mappings_by_service[service_name] = []
            mappings_by_service[service_name].append(mapping)

        return mappings_by_service

    def get_mapping_report(self) -> Dict[str, Any]:
        """Generate a report on extracted port mappings."""
        total_mappings = len(self.extracted_mappings)
        sources: Dict[str, int] = {}
        confidence_levels: Dict[str, int] = {}

        for mapping in self.extracted_mappings:
            source = mapping.source.value
            sources[source] = sources.get(source, 0) + 1

            if mapping.confidence >= 0.9:
                level = "high"
            elif mapping.confidence >= 0.7:
                level = "medium"
            else:
                level = "low"
            confidence_levels[level] = confidence_levels.get(level, 0) + 1

        return {
            "total_mappings": total_mappings,
            "unique_services": len(self.get_port_mappings_by_service()),
            "sources": sources,
            "confidence_levels": confidence_levels,
            "files_processed": len(set(m.source_file for m in self.extracted_mappings))
        }
