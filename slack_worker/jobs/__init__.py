"""
Slack Worker Jobs
=================
This package contains all scheduled job implementations.

Each job should:
1. Inherit from BaseJob
2. Implement the execute() method
3. Use lock manager for distributed coordination
4. Be independently schedulable
"""

from slack_worker.jobs.base_job import BaseJob

__all__ = ['BaseJob']

