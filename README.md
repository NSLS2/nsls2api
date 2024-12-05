# NSLS-II Facility API

IGNORE THIS

This is the repository for the NSLS-II Facility API codebase. 

## Current Status

[![Integration Tests for Deployed API](https://github.com/NSLS2/nsls2api/actions/workflows/test-production-deployment.yml/badge.svg)](https://github.com/NSLS2/nsls2api/actions/workflows/test-production-deployment.yml)

## Developer Notes 

### Updating Dependencies

The project uses `pip-compile` to manage the `requirements.txt` and `requirements-dev.txt`. 
In order to upgrade the packages you will need to install `pip-tools`.  Then to upgrade simply run 

```
pip-compile requirements-dev.in --upgrade
pip-compile requirements.in --upgrade
```

