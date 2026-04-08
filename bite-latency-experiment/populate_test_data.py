#!/usr/bin/env python3
"""
Database Population Script for Load Testing
Populates the database with realistic test data for JMeter tests
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.dirname(__file__))
django.setup()

from django.core.management import call_command
from reports.models import Report
from datetime import datetime, timedelta
import random

def populate_database(num_projects=50, months_per_project=12):
    """
    Populate database with test data

    Args:
        num_projects: Number of projects to create
        months_per_project: Number of months of data per project
    """
    print(f"Populating database with {num_projects} projects, {months_per_project} months each...")

    # Check if seed_reports management command exists
    try:
        print("\nUsing Django management command to seed data...")
        call_command('seed_reports',
                    projects=num_projects,
                    months=months_per_project,
                    replace=True)
        print("✓ Data seeded successfully via management command")

    except Exception as e:
        print(f"Management command not available: {e}")
        print("Creating test data manually...")

        # Manual population if command doesn't exist
        Report.objects.all().delete()

        base_date = datetime.now()
        reports_created = 0

        for project_num in range(1, num_projects + 1):
            project_id = f"proj-{project_num:03d}"

            for month_offset in range(months_per_project):
                month_date = base_date - timedelta(days=30 * month_offset)
                month_str = month_date.strftime('%Y-%m')

                # Create realistic report data
                report_data = {
                    'total_latency': random.randint(100, 5000),
                    'average_latency': round(random.uniform(10, 500), 2),
                    'max_latency': random.randint(500, 10000),
                    'min_latency': random.randint(5, 100),
                    'request_count': random.randint(1000, 100000),
                    'error_count': random.randint(0, 100),
                    'success_rate': round(random.uniform(95, 100), 2)
                }

                Report.objects.create(
                    project_id=project_id,
                    month=month_str,
                    data=report_data
                )
                reports_created += 1

                if reports_created % 100 == 0:
                    print(f"Created {reports_created} reports...")

        print(f"✓ Created {reports_created} reports manually")

    # Display summary
    total_reports = Report.objects.count()
    print(f"\n" + "="*60)
    print(f"DATABASE POPULATION COMPLETE")
    print(f"="*60)
    print(f"Total Reports: {total_reports}")
    print(f"Projects: {num_projects}")
    print(f"Months per project: {months_per_project}")
    print(f"\nSample project IDs:")
    for i in range(1, min(6, num_projects + 1)):
        print(f"  - proj-{i:03d}")
    print(f"\nSample months:")
    base_date = datetime.now()
    for i in range(min(3, months_per_project)):
        month_date = base_date - timedelta(days=30 * i)
        print(f"  - {month_date.strftime('%Y-%m')}")

    print(f"\nTest URLs:")
    print(f"  curl -H 'apikey: jmeter-load-test-key-67890' \\")
    print(f"    'http://localhost:8000/api/report/?projectId=proj-001&month={base_date.strftime('%Y-%m')}'")
    print(f"="*60)

def warm_cache(limit=100):
    """Warm up the cache with most common queries"""
    print(f"\nWarming cache with {limit} most common queries...")

    try:
        call_command('warm_cache', limit=limit)
        print("✓ Cache warmed successfully")
    except Exception as e:
        print(f"Cache warming not available: {e}")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Populate database with test data for load testing')
    parser.add_argument('--projects', type=int, default=100,
                       help='Number of projects to create (default: 100)')
    parser.add_argument('--months', type=int, default=12,
                       help='Number of months per project (default: 12)')
    parser.add_argument('--warm-cache', action='store_true',
                       help='Warm cache after populating')
    parser.add_argument('--cache-limit', type=int, default=100,
                       help='Number of queries to cache (default: 100)')

    args = parser.parse_args()

    try:
        populate_database(args.projects, args.months)

        if args.warm_cache:
            warm_cache(args.cache_limit)

        print("\n✓ All done! Database is ready for load testing.")

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
