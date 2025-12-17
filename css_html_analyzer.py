#!/usr/bin/env python3
"""
CSS/HTML Cleanup Analyzer

Analyzes HTML and CSS files to identify:
- Unused CSS selectors
- Duplicate CSS rules
- Overly specific selectors
- Dead code opportunities
"""

import re
import os
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Set, Tuple
import cssutils
import logging
from bs4 import BeautifulSoup

# Suppress cssutils warnings
cssutils.log.setLevel(logging.CRITICAL)


class CSSHTMLAnalyzer:
    def __init__(self, html_dir: str, css_dir: str):
        self.html_dir = Path(html_dir)
        self.css_dir = Path(css_dir)
        self.html_classes = set()
        self.html_ids = set()
        self.html_tags = set()
        self.css_selectors = defaultdict(list)  # selector -> list of (file, line)
        self.duplicate_rules = defaultdict(list)  # rule_hash -> list of locations
        
    def parse_html_files(self):
        """Extract all classes, IDs, and tags from HTML files"""
        for html_file in self.html_dir.rglob('*.html'):
            with open(html_file, 'r', encoding='utf-8') as f:
                try:
                    soup = BeautifulSoup(f.read(), 'html.parser')
                    
                    # Extract classes
                    for tag in soup.find_all(class_=True):
                        classes = tag.get('class', [])
                        if isinstance(classes, list):
                            self.html_classes.update(classes)
                        else:
                            self.html_classes.add(classes)
                    
                    # Extract IDs
                    for tag in soup.find_all(id=True):
                        self.html_ids.add(tag.get('id'))
                    
                    # Extract tag names
                    for tag in soup.find_all():
                        self.html_tags.add(tag.name)
                        
                except Exception as e:
                    print(f"Error parsing {html_file}: {e}")
    
    def parse_css_files(self):
        """Parse CSS files and extract selectors and rules"""
        for css_file in self.css_dir.rglob('*.css'):
            with open(css_file, 'r', encoding='utf-8') as f:
                try:
                    sheet = cssutils.parseString(f.read())
                    
                    for rule in sheet:
                        if rule.type == rule.STYLE_RULE:
                            selector = rule.selectorText
                            # Store selector location
                            self.css_selectors[selector].append(str(css_file))
                            
                            # Check for duplicate rules (same selector + same properties)
                            rule_hash = self._hash_rule(selector, rule.style.cssText)
                            self.duplicate_rules[rule_hash].append(
                                (str(css_file), selector)
                            )
                            
                except Exception as e:
                    print(f"Error parsing {css_file}: {e}")
    
    def _hash_rule(self, selector: str, css_text: str) -> str:
        """Create a hash of a CSS rule for duplicate detection"""
        # Normalize whitespace and sort properties for consistent comparison
        normalized = re.sub(r'\s+', ' ', css_text).strip()
        return f"{selector}|{normalized}"
    
    def _extract_selector_components(self, selector: str) -> Dict[str, Set[str]]:
        """Extract classes, IDs, and tags from a CSS selector"""
        components = {
            'classes': set(),
            'ids': set(),
            'tags': set()
        }
        
        # Remove pseudo-classes and pseudo-elements for analysis
        cleaned = re.sub(r'::?[\w-]+(\([^)]*\))?', '', selector)
        
        # Extract classes
        components['classes'] = set(re.findall(r'\.([a-zA-Z0-9_-]+)', cleaned))
        
        # Extract IDs
        components['ids'] = set(re.findall(r'#([a-zA-Z0-9_-]+)', cleaned))
        
        # Extract tags (simplified - doesn't handle all edge cases)
        # Get tag names that aren't part of other selectors
        tags = re.findall(r'\b([a-z][a-z0-9]*)\b', cleaned.lower())
        components['tags'] = set(tags) - {'not', 'is', 'where', 'has'}
        
        return components
    
    def find_unused_selectors(self) -> List[Dict]:
        """Identify CSS selectors that don't match any HTML elements"""
        unused = []
        
        for selector, files in self.css_selectors.items():
            components = self._extract_selector_components(selector)
            
            # Check if any component exists in HTML
            class_used = any(cls in self.html_classes for cls in components['classes'])
            id_used = any(id_ in self.html_ids for id_ in components['ids'])
            tag_used = any(tag in self.html_tags for tag in components['tags'])
            
            # If selector has components but none are used, mark as unused
            has_components = bool(components['classes'] or components['ids'] or components['tags'])
            if has_components and not (class_used or id_used or tag_used):
                unused.append({
                    'selector': selector,
                    'files': files,
                    'components': components
                })
        
        return unused
    
    def find_duplicate_selectors(self) -> List[Dict]:
        """Find selectors defined in multiple places"""
        duplicates = []
        
        for selector, files in self.css_selectors.items():
            if len(files) > 1:
                duplicates.append({
                    'selector': selector,
                    'count': len(files),
                    'files': files
                })
        
        return duplicates
    
    def find_duplicate_rules(self) -> List[Dict]:
        """Find identical CSS rules (same selector + properties)"""
        duplicates = []
        
        for rule_hash, locations in self.duplicate_rules.items():
            if len(locations) > 1:
                duplicates.append({
                    'rule': rule_hash.split('|')[0],  # selector
                    'count': len(locations),
                    'locations': locations
                })
        
        return duplicates
    
    def analyze(self) -> Dict:
        """Run full analysis and return results"""
        print("Parsing HTML files...")
        self.parse_html_files()
        
        print("Parsing CSS files...")
        self.parse_css_files()
        
        print("Analyzing for issues...")
        results = {
            'unused_selectors': self.find_unused_selectors(),
            'duplicate_selectors': self.find_duplicate_selectors(),
            'duplicate_rules': self.find_duplicate_rules(),
            'stats': {
                'total_css_selectors': len(self.css_selectors),
                'total_html_classes': len(self.html_classes),
                'total_html_ids': len(self.html_ids),
                'total_html_tags': len(self.html_tags)
            }
        }
        
        return results
    
    def print_report(self, results: Dict):
        """Print a formatted report of findings"""
        print("\n" + "="*80)
        print("CSS/HTML CLEANUP ANALYSIS REPORT")
        print("="*80)
        
        # Stats
        stats = results['stats']
        print(f"\nSTATISTICS:")
        print(f"  Total CSS Selectors: {stats['total_css_selectors']}")
        print(f"  HTML Classes Found: {stats['total_html_classes']}")
        print(f"  HTML IDs Found: {stats['total_html_ids']}")
        print(f"  HTML Tags Found: {stats['total_html_tags']}")
        
        # Unused selectors
        unused = results['unused_selectors']
        print(f"\n{'='*80}")
        print(f"UNUSED SELECTORS: {len(unused)}")
        print(f"{'='*80}")
        if unused:
            for item in unused[:20]:  # Show first 20
                print(f"\n  Selector: {item['selector']}")
                print(f"  Files: {', '.join(set(item['files']))}")
                if item['components']['classes']:
                    print(f"  Classes: {', '.join(item['components']['classes'])}")
                if item['components']['ids']:
                    print(f"  IDs: {', '.join(item['components']['ids'])}")
            if len(unused) > 20:
                print(f"\n  ... and {len(unused) - 20} more")
        else:
            print("  None found!")
        
        # Duplicate selectors
        dupes = results['duplicate_selectors']
        print(f"\n{'='*80}")
        print(f"DUPLICATE SELECTORS: {len(dupes)}")
        print(f"{'='*80}")
        if dupes:
            for item in dupes[:20]:
                print(f"\n  Selector: {item['selector']}")
                print(f"  Defined {item['count']} times in:")
                for f in set(item['files']):
                    print(f"    - {f}")
            if len(dupes) > 20:
                print(f"\n  ... and {len(dupes) - 20} more")
        else:
            print("  None found!")
        
        # Duplicate rules
        dupe_rules = results['duplicate_rules']
        print(f"\n{'='*80}")
        print(f"DUPLICATE RULES (identical selector + properties): {len(dupe_rules)}")
        print(f"{'='*80}")
        if dupe_rules:
            for item in dupe_rules[:20]:
                print(f"\n  Rule: {item['rule']}")
                print(f"  Appears {item['count']} times in:")
                for loc in item['locations']:
                    print(f"    - {loc[0]}")
            if len(dupe_rules) > 20:
                print(f"\n  ... and {len(dupe_rules) - 20} more")
        else:
            print("  None found!")
        
        print("\n" + "="*80)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Analyze HTML and CSS files for cleanup opportunities'
    )
    parser.add_argument('html_dir', help='Directory containing HTML files')
    parser.add_argument('css_dir', help='Directory containing CSS files')
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    
    args = parser.parse_args()
    
    analyzer = CSSHTMLAnalyzer(args.html_dir, args.css_dir)
    results = analyzer.analyze()
    
    if args.json:
        import json
        print(json.dumps(results, indent=2, default=str))
    else:
        analyzer.print_report(results)


if __name__ == '__main__':
    main()