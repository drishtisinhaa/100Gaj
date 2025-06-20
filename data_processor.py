import pandas as pd
import os
import logging
from typing import List, Dict, Optional

class DataProcessor:
    """Handles CSV data processing and search functionality"""

    def __init__(self):
        self.df = None
        self.load_data()

    def load_data(self):
        """Load and process the CSV data"""
        try:
            csv_path = 'data/delhi_locations.csv'
            if not os.path.exists(csv_path):
                csv_path = 'attached_assets/Delhi_Comprehensive_Livability_167_Locations_1749628652925.csv'

            if os.path.exists(csv_path):
                self.df = pd.read_csv(csv_path)
                self.df = self.df.fillna('')
                # Normalize text fields for matching
                self.df['Location'] = self.df['Location'].str.lower().str.strip()
                self.df['Zone'] = self.df['Zone'].str.lower().str.strip()
                logging.info(f"Loaded {len(self.df)} locations from CSV")
            else:
                logging.error("CSV file not found")
                self.df = pd.DataFrame()

        except Exception as e:
            logging.error(f"Error loading CSV data: {str(e)}")
            self.df = pd.DataFrame()

    def search_locations(self, query: str, limit: int = 10) -> List[Dict]:
        """Search locations based on query string"""
        if self.df.empty:
            return []

        query = query.lower().strip()

        mask = (
            self.df['Location'].str.contains(query, na=False) |
            self.df['Zone'].str.contains(query, na=False)
        )

        results = self.df[mask].head(limit)

        search_results = []
        for _, row in results.iterrows():
            search_results.append({
                'location': row['Location'].title(),
                'zone': row['Zone'].title(),
                'crime_level': row['Crime_Level'],
                'safety_rating': row['Safety_Rating_out_of_10']
            })

        return search_results

    def get_location_details(self, location_name: str) -> Optional[Dict]:
        """Get detailed information for a specific location"""
        if self.df.empty:
            return None

        location_name = location_name.lower().strip()
        mask = self.df['Location'] == location_name
        matches = self.df[mask]

        if matches.empty:
            return None

        row = matches.iloc[0]

        pros = self._parse_pros_cons(row.get('Detailed_Pros', ''))
        cons = self._parse_pros_cons(row.get('Detailed_Cons', ''))

        return {
            'location': row['Location'].title(),
            'zone': row['Zone'].title(),
            'crime_level': row['Crime_Level'],
            'total_crimes': int(row['Total_Crimes']) if pd.notna(row['Total_Crimes']) else 0,
            'safety_rating': float(row['Safety_Rating_out_of_10']) if pd.notna(row['Safety_Rating_out_of_10']) else 0,
            'crime_rating': float(row['Crime_Rating_out_of_10']) if pd.notna(row['Crime_Rating_out_of_10']) else 0,
            'water_clogging': row['Water_Clogging_Issues'],
            'electricity_issues': row['Electricity_Issues'],
            'pros': pros,
            'cons': cons
        }

    def get_all_locations(self) -> List[str]:
        """Get list of all location names for autocomplete"""
        if self.df.empty:
            return []

        return sorted([loc.title() for loc in self.df['Location'].unique().tolist()])

    def _parse_pros_cons(self, text: str) -> List[str]:
        """Parse pros/cons text into list of items"""
        if not text or pd.isna(text):
            return []

        return [item.strip() for item in str(text).split(';') if item.strip()]

    def get_zone_statistics(self) -> Dict:
        """Get statistics by zone"""
        if self.df.empty:
            return {}

        zone_stats = {}
        for zone in self.df['Zone'].unique():
            zone_data = self.df[self.df['Zone'] == zone]
            zone_stats[zone.title()] = {
                'total_locations': len(zone_data),
                'avg_safety_rating': float(zone_data['Safety_Rating_out_of_10'].mean()),
                'avg_crime_rating': float(zone_data['Crime_Rating_out_of_10'].mean()),
                'crime_level_distribution': zone_data['Crime_Level'].value_counts().to_dict()
            }

        return zone_stats
