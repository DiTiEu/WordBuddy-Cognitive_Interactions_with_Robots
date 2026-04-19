# Security Policy

## Supported Versions

This project is an academic research prototype. Only the latest version on the
`main` branch receives attention for security issues.

| Version | Supported |
|---------|-----------|
| main    | Yes       |

## Reporting a Vulnerability

This system controls physical hardware (a UR3 collaborative robot arm). If you
discover a vulnerability — especially one that could cause unsafe robot behavior,
unauthorized control, or data exposure — please report it responsibly.

**Do not open a public GitHub issue for security vulnerabilities.**

Instead, email **terzi.diego02@gmail.com** with:
- A description of the vulnerability and its potential impact
- Steps to reproduce (if applicable)
- Any suggested mitigations

You will receive an acknowledgement within 7 days. Because this is an academic
project with no commercial deployment, response timelines may vary.

## Scope

Areas of particular concern given the nature of this project:

- **Robot control interface** (`src/new_robot_control.py`): unauthorized socket
  commands could cause physical movement.
- **Network configuration** (`data/config.yaml`): the robot IP and port are
  stored in plaintext; do not expose this file publicly if your robot is on a
  reachable network.
- **Camera input**: the vision pipeline processes frames from a connected camera;
  adversarial inputs to the CNN classifier are in scope.

## Out of Scope

- Issues in third-party dependencies (report those upstream)
- Vulnerabilities that require physical access to the robot cell
