# src/visualizer.py
import logging
import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from urllib.parse import urlparse

#Plot types in: https://matplotlib.org/stable/plot_types/index.html

def clean_url_label(url):
    try:
        domain = urlparse(url).netloc
        return domain.replace("www.", "")
    except:
        return url[:20] + "..."

def generate_landscape_graphs(df, landscape_name, features_list):
    """
    Generates summary graphs for the competitive landscape.
    1. Feature Adoption Rate (How many companies have Feature X?)
    2. Company Capabilities Score (Who has the most features?)
    """
    logging.info(f"Generating visualization for {landscape_name}...")
    
    # 1. Prepare Data
    # Create a copy to avoid modifying the original
    plot_df = df.copy()
    
    # Clean up company names for the chart
    plot_df['Company_Label'] = plot_df['URL'].apply(clean_url_label)
    
    # Convert "Yes"/"No" text to numeric (1/0)
    # This handles "Yes", "yes", "YES" and treats anything else (No, Unknown, Error) as 0
    numeric_df = pd.DataFrame()
    numeric_df['Company_Label'] = plot_df['Company_Label']
    
    for feature in features_list:
        if feature in plot_df.columns:
            # Map Yes to 1, everything else to 0
            numeric_df[feature] = plot_df[feature].astype(str).apply(
                lambda x: 1 if 'yes' in x.lower() else 0
            )

    # -------------------------------------------------------
    # Graph 1: Feature Prevalence (Market Maturity)
    # -------------------------------------------------------
    try:
        # Calculate sum of 'Yes' for each feature
        feature_sums = numeric_df[features_list].sum().sort_values(ascending=True)
        total_companies = len(plot_df)
        
        plt.figure(figsize=(10, 6))
        sns.set_style("whitegrid")
        
        # Create Bar Plot
        ax = feature_sums.plot(kind='barh', color="#7125cd")
        
        plt.title(f"Feature Adoption in {landscape_name} Landscape", fontsize=14, pad=20)
        plt.xlabel("Number of Companies Offering Feature", fontsize=10)
        plt.xlim(0, total_companies + 1) # Set limit slightly higher than max
        
        # Add text labels on bars
        for i, v in enumerate(feature_sums):
            ax.text(v + 0.1, i, f"{v}/{total_companies} ({int(v/total_companies*100)}%)", 
                    va='center', fontsize=9)
            
        plt.tight_layout()
        outfile_feat = os.path.join("output", f"{landscape_name.replace(' ', '_')}_feature_adoption.png")
        plt.savefig(outfile_feat, dpi=300)
        plt.close()
        logging.info(f"Saved adoption graph: {outfile_feat}")
        
    except Exception as e:
        logging.error(f"Could not generate adoption graph: {e}")

    # -------------------------------------------------------
    # Graph 2: Company Leaderboard
    # -------------------------------------------------------
    try:
        # Calculate total score per company
        numeric_df['Total_Score'] = numeric_df[features_list].sum(axis=1)
        
        # Sort by score descending
        leaderboard = numeric_df.sort_values('Total_Score', ascending=False)
        
        plt.figure(figsize=(10, len(leaderboard) * 0.5 + 2)) # Dynamic height based on N companies
        sns.set_style("whitegrid")
        
        # Create Bar Plot
        sns.barplot(x='Total_Score', y='Company_Label', data=leaderboard, palette='viridis')
        
        plt.title(f"Feature Completeness by Company", fontsize=14, pad=20)
        plt.xlabel(f"Number of Features (out of {len(features_list)})", fontsize=10)
        plt.ylabel("")
        
        plt.tight_layout()
        outfile_rank = os.path.join("output", f"{landscape_name.replace(' ', '_')}_company_ranking.png")
        plt.savefig(outfile_rank, dpi=300)
        plt.close()
        logging.info(f"Saved ranking graph: {outfile_rank}")
        
        # -------------------------------------------------------
        # Text Summary
        # -------------------------------------------------------
        print("\nLANDSCAPE INSIGHTS:")
        
        # Best Company
        top_company = leaderboard.iloc[0]
        logging.info(f"      - Leader: {top_company['Company_Label']} coverage: {int(top_company['Total_Score'])}/{len(features_list)} features")
        
        # Most Common Feature
        most_common = feature_sums.index[-1]
        most_common_count = feature_sums.iloc[-1]
        logging.info(f"      - Most Common Feature: '{most_common}' ({most_common_count}/{total_companies} companies)")
        
        # Rarest Feature
        least_common = feature_sums.index[0]
        least_common_count = feature_sums.iloc[0]
        logging.info(f"      - Rarest Feature: '{least_common}' ({least_common_count}/{total_companies} companies)")

    except Exception as e:
        logging.error(f"Could not generate ranking graph: {e}")