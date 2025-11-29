"""
data loader - handles loading and preprocessing of facebook ads dataset
"""
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
from pathlib import Path


class DataLoader:
    """loads and preprocesses facebook ads dataset"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.data_path = config['data']['path']
        self.sample_size = config['data'].get('sample_size')
        self.df: Optional[pd.DataFrame] = None
        
    def load_data(self) -> pd.DataFrame:
        """
        load the facebook ads dataset
        
        returns:
            dataframe with cleaned and preprocessed data
        """
        if self.df is not None:
            return self.df
            
        # load csv
        df = pd.read_csv(self.data_path)
        
        # clean and preprocess
        df = self._preprocess(df)
        
        # sample if configured
        if self.sample_size and len(df) > self.sample_size:
            df = df.sample(n=self.sample_size, random_state=self.config.get('random_seed', 42))
        
        self.df = df
        return self.df
    
    def _preprocess(self, df: pd.DataFrame) -> pd.DataFrame:
        """clean and preprocess the dataset"""
        # convert date column
        df['date'] = pd.to_datetime(df['date'])
        
        # fill missing numeric values with 0
        numeric_cols = ['spend', 'impressions', 'clicks', 'purchases', 'revenue', 'roas', 'ctr']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        # standardize campaign names (normalize variations)
        df['campaign_name_normalized'] = df['campaign_name'].str.lower().str.strip()
        df['campaign_name_normalized'] = df['campaign_name_normalized'].str.replace(r'\s+', ' ', regex=True)
        df['campaign_name_normalized'] = df['campaign_name_normalized'].str.replace(r'[_\-]', ' ', regex=True)
        
        # fill missing categorical values
        categorical_cols = ['creative_type', 'audience_type', 'platform', 'country']
        for col in categorical_cols:
            if col in df.columns:
                df[col] = df[col].fillna('Unknown')
        
        return df
    
    def get_summary_stats(self) -> Dict[str, Any]:
        """
        get comprehensive summary statistics
        
        returns:
            dictionary with summary statistics
        """
        if self.df is None:
            self.load_data()
            
        df = self.df
        
        return {
            "date_range": {
                "start": df['date'].min().strftime('%Y-%m-%d'),
                "end": df['date'].max().strftime('%Y-%m-%d')
            },
            "total_campaigns": df['campaign_name'].nunique(),
            "total_records": len(df),
            "overall_metrics": {
                "total_spend": float(df['spend'].sum()),
                "total_revenue": float(df['revenue'].sum()),
                "total_impressions": int(df['impressions'].sum()),
                "total_clicks": int(df['clicks'].sum()),
                "total_purchases": int(df['purchases'].sum()),
                "overall_roas": float(df['revenue'].sum() / df['spend'].sum()) if df['spend'].sum() > 0 else 0,
                "avg_ctr": float(df['ctr'].mean()),
                "avg_roas": float(df['roas'].mean())
            },
            "breakdowns": {
                "creative_types": df['creative_type'].unique().tolist(),
                "audience_types": df['audience_type'].unique().tolist(),
                "platforms": df['platform'].unique().tolist(),
                "countries": df['country'].unique().tolist()
            }
        }
    
    def get_time_series_metrics(self, metric: str = 'roas') -> Dict[str, float]:
        """
        get time series data for a specific metric
        
        args:
            metric: metric to aggregate ('roas', 'ctr', 'spend', 'purchases')
            
        returns:
            dictionary with date -> metric value
        """
        if self.df is None:
            self.load_data()
            
        if metric not in self.df.columns:
            raise ValueError(f"Metric {metric} not found in dataset")
        
        # aggregate by date
        if metric in ['spend', 'purchases', 'revenue']:
            daily = self.df.groupby('date')[metric].sum()
        else:
            daily = self.df.groupby('date')[metric].mean()
        
        return {date.strftime('%Y-%m-%d'): float(value) for date, value in daily.items()}
    
    def get_campaign_performance(self) -> Dict[str, Dict[str, Any]]:
        """
        get performance breakdown by campaign
        
        returns:
            dictionary with campaign -> performance metrics
        """
        if self.df is None:
            self.load_data()
            
        results = {}
        
        for campaign in self.df['campaign_name'].unique():
            campaign_df = self.df[self.df['campaign_name'] == campaign]
            
            results[campaign] = {
                "total_spend": float(campaign_df['spend'].sum()),
                "total_revenue": float(campaign_df['revenue'].sum()),
                "total_purchases": int(campaign_df['purchases'].sum()),
                "total_impressions": int(campaign_df['impressions'].sum()),
                "total_clicks": int(campaign_df['clicks'].sum()),
                "avg_roas": float(campaign_df['roas'].mean()),
                "avg_ctr": float(campaign_df['ctr'].mean()),
                "record_count": len(campaign_df),
                "creative_types": campaign_df['creative_type'].unique().tolist(),
                "audience_types": campaign_df['audience_type'].unique().tolist()
            }
        
        return results
    
    def get_creative_performance(self) -> Dict[str, Dict[str, Any]]:
        """
        get performance breakdown by creative type
        
        returns:
            dictionary with creative_type -> performance metrics
        """
        if self.df is None:
            self.load_data()
            
        results = {}
        
        for creative_type in self.df['creative_type'].unique():
            creative_df = self.df[self.df['creative_type'] == creative_type]
            
            results[creative_type] = {
                "total_spend": float(creative_df['spend'].sum()),
                "total_revenue": float(creative_df['revenue'].sum()),
                "avg_roas": float(creative_df['roas'].mean()),
                "avg_ctr": float(creative_df['ctr'].mean()),
                "count": len(creative_df)
            }
        
        return results
    
    def get_audience_performance(self) -> Dict[str, Dict[str, Any]]:
        """
        get performance breakdown by audience type
        
        returns:
            dictionary with audience_type -> performance metrics
        """
        if self.df is None:
            self.load_data()
            
        results = {}
        
        for audience_type in self.df['audience_type'].unique():
            audience_df = self.df[self.df['audience_type'] == audience_type]
            
            results[audience_type] = {
                "total_spend": float(audience_df['spend'].sum()),
                "total_revenue": float(audience_df['revenue'].sum()),
                "avg_roas": float(audience_df['roas'].mean()),
                "avg_ctr": float(audience_df['ctr'].mean()),
                "count": len(audience_df)
            }
        
        return results
    
    def detect_anomalies(self, metric: str = 'roas', threshold: float = 1.5) -> Dict[str, Any]:
        """
        detect anomalies in a metric using iqr method
        
        args:
            metric: metric to analyze
            threshold: iqr multiplier for anomaly detection
            
        returns:
            dictionary with anomaly information
        """
        if self.df is None:
            self.load_data()
            
        values = self.df[metric]
        
        Q1 = values.quantile(0.25)
        Q3 = values.quantile(0.75)
        IQR = Q3 - Q1
        
        lower_bound = Q1 - threshold * IQR
        upper_bound = Q3 + threshold * IQR
        
        anomalies_mask = (values < lower_bound) | (values > upper_bound)
        anomaly_df = self.df[anomalies_mask]
        
        anomaly_list = []
        for _, row in anomaly_df.iterrows():
            anomaly_list.append({
                "date": row['date'].strftime('%Y-%m-%d'),
                "campaign_name": row['campaign_name'],
                "roas": float(row['roas']),
                "ctr": float(row['ctr']),
                "spend": float(row['spend']),
                "revenue": float(row['revenue'])
            })
        
        return {
            "metric": metric,
            "lower_bound": float(lower_bound),
            "upper_bound": float(upper_bound),
            "anomaly_count": len(anomaly_df),
            "anomalies": anomaly_list[:20]  # limit to 20 anomalies
        }
    
    def get_low_ctr_campaigns(self, threshold: float) -> pd.DataFrame:
        """
        get campaigns with ctr below threshold
        
        args:
            threshold: ctr threshold
            
        returns:
            dataframe with low-ctr campaign records
        """
        if self.df is None:
            self.load_data()
            
        low_ctr = self.df[self.df['ctr'] < threshold].copy()
        return low_ctr.sort_values('ctr')
    
    def get_low_roas_campaigns(self, threshold: float) -> pd.DataFrame:
        """
        get campaigns with roas below threshold
        
        args:
            threshold: roas threshold
            
        returns:
            dataframe with low-roas campaign records
        """
        if self.df is None:
            self.load_data()
            
        low_roas = self.df[self.df['roas'] < threshold].copy()
        return low_roas.sort_values('roas')
    
    def get_top_performers(self, metric: str = 'roas', n: int = 10) -> pd.DataFrame:
        """
        get top performing records by a metric
        
        args:
            metric: metric to sort by
            n: number of records to return
            
        returns:
            dataframe with top performers
        """
        if self.df is None:
            self.load_data()
            
        return self.df.nlargest(n, metric)
    
    def get_bottom_performers(self, metric: str = 'roas', n: int = 10) -> pd.DataFrame:
        """
        get bottom performing records by a metric
        
        args:
            metric: metric to sort by
            n: number of records to return
            
        returns:
            dataframe with bottom performers
        """
        if self.df is None:
            self.load_data()
            
        return self.df.nsmallest(n, metric)
    
    def get_correlation_matrix(self) -> Dict[str, Dict[str, float]]:
        """
        get correlation matrix for numeric columns
        
        returns:
            nested dictionary with correlations
        """
        if self.df is None:
            self.load_data()
            
        numeric_cols = ['spend', 'impressions', 'clicks', 'ctr', 'purchases', 'revenue', 'roas']
        corr_matrix = self.df[numeric_cols].corr()
        
        return corr_matrix.to_dict()
    
    def get_weekly_trends(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        get weekly aggregated trends
        
        returns:
            dictionary with weekly metrics
        """
        if self.df is None:
            self.load_data()
            
        df = self.df.copy()
        df['week'] = df['date'].dt.isocalendar().week
        df['year'] = df['date'].dt.year
        
        weekly = df.groupby(['year', 'week']).agg({
            'spend': 'sum',
            'revenue': 'sum',
            'purchases': 'sum',
            'roas': 'mean',
            'ctr': 'mean'
        }).reset_index()
        
        return {
            "weekly_data": weekly.to_dict(orient='records')
        }
