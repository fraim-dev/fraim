#!/usr/bin/env python3
"""
Test script for CVE Data Generator with real code extraction

This script demonstrates the enhanced CVE data generator that can extract
real vulnerable and fixed code from CVE references.
"""

import logging
import tempfile
from pathlib import Path
from . import CVETrainingDataManager

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_cve_code_extraction() -> None:
    """Test CVE data generation with real code extraction."""
    logger.info("Testing CVE data generation with code extraction...")
    
    # Create temporary output directory
    with tempfile.TemporaryDirectory() as temp_dir:
        output_dir = Path(temp_dir) / "test_output"
        
        # Initialize manager with code extraction enabled
        manager = CVETrainingDataManager(extract_code=True)
        
        try:
            # Generate training data for a few vulnerability types
            # Using smaller numbers for testing
            manager.generate_training_data(
                vulnerability_types=['SQL Injection', 'XSS'],
                output_dir=output_dir,
                max_cves_per_type=3,  # Small number for testing
                severity='HIGH'  # Focus on high severity for better results
            )
            
            # Check if files were created
            scanner_file = output_dir / "scanner_training_data.csv"
            triager_file = output_dir / "triager_training_data.csv"
            
            if scanner_file.exists():
                logger.info(f"Scanner training data created: {scanner_file}")
                with open(scanner_file, 'r') as f:
                    lines = f.readlines()
                    logger.info(f"Scanner file has {len(lines)} lines")
            
            if triager_file.exists():
                logger.info(f"Triager training data created: {triager_file}")
                with open(triager_file, 'r') as f:
                    lines = f.readlines()
                    logger.info(f"Triager file has {len(lines)} lines")
            
            logger.info("Test completed successfully!")
            
        except Exception as e:
            logger.error(f"Test failed: {e}")
            raise

def test_without_code_extraction() -> None:
    """Test CVE data generation without code extraction (templates only)."""
    logger.info("Testing CVE data generation without code extraction...")
    
    # Create temporary output directory
    with tempfile.TemporaryDirectory() as temp_dir:
        output_dir = Path(temp_dir) / "test_output_templates"
        
        # Initialize manager with code extraction disabled
        manager = CVETrainingDataManager(extract_code=False)
        
        try:
            # Generate training data using templates only
            manager.generate_training_data(
                vulnerability_types=['SQL Injection', 'XSS'],
                output_dir=output_dir,
                max_cves_per_type=3,
                severity='HIGH'
            )
            
            logger.info("Template-only test completed successfully!")
            
        except Exception as e:
            logger.error(f"Template test failed: {e}")
            raise

if __name__ == "__main__":
    print("🧪 Testing Enhanced CVE Data Generator")
    print("=" * 50)
    
    try:
        # Test with code extraction
        test_cve_code_extraction()
        print("\n" + "=" * 50)
        
        # Test without code extraction
        test_without_code_extraction()
        
        print("\n✅ All tests passed!")
        
    except Exception as e:
        print(f"\n❌ Tests failed: {e}")
        exit(1)