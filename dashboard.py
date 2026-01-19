
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
import glob
from datetime import datetime

# Streamlit Page Config
st.set_page_config(
    page_title="OTT Trend Dashboard",
    page_icon="📊",
    layout="wide"
)

# Constants & Paths
DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
TREND_DIR = os.path.join(DATA_DIR, 'datalab')
BLOG_DIR = os.path.join(DATA_DIR, 'blog')
NEWS_DIR = os.path.join(DATA_DIR, 'news')

# Utility Functions
@st.cache_data
def load_all_data():
    """Load all CSV files from data directories and combine them."""
    data = {'trend': pd.DataFrame(), 'blog': pd.DataFrame(), 'news': pd.DataFrame()}
    
    # Load Trends
    trend_files = glob.glob(os.path.join(TREND_DIR, '*.csv'))
    trend_dfs = []
    for f in trend_files:
        try:
            # Extract keyword from filename: trend_{keyword}_{date}.csv
            filename = os.path.basename(f)
            parts = filename.split('_')
            if len(parts) >= 3:
                keyword = parts[1]
                df = pd.read_csv(f)
                df['keyword'] = keyword
                
                # Convert date column
                if 'period' in df.columns:
                    df['date'] = pd.to_datetime(df['period'])
                trend_dfs.append(df)
        except Exception as e:
            print(f"Error loading {f}: {e}")
            
    if trend_dfs:
        data['trend'] = pd.concat(trend_dfs, ignore_index=True)

    # Load Blogs
    blog_files = glob.glob(os.path.join(BLOG_DIR, '*.csv'))
    blog_dfs = []
    for f in blog_files:
        try:
            filename = os.path.basename(f)
            parts = filename.split('_')
            if len(parts) >= 3:
                keyword = parts[2] # blog_review_{keyword}_{date}.csv
                df = pd.read_csv(f)
                df['keyword'] = keyword
                 # Convert date column
                if 'postdate' in df.columns:
                    # Naver API returns YYYYMMDD string usually
                    df['date'] = pd.to_datetime(df['postdate'], format='%Y%m%d', errors='coerce')
                blog_dfs.append(df)
        except Exception as e:
            print(f"Error loading {f}: {e}")

    if blog_dfs:
        data['blog'] = pd.concat(blog_dfs, ignore_index=True)

    # Load News
    news_files = glob.glob(os.path.join(NEWS_DIR, '*.csv'))
    news_dfs = []
    for f in news_files:
        try:
            filename = os.path.basename(f)
            parts = filename.split('_')
            if len(parts) >= 3:
                keyword = parts[2] # news_issue_{keyword}_{date}.csv
                df = pd.read_csv(f)
                df['keyword'] = keyword
                # Convert date column. PubDate is often 'Mon, 29 Jan 2024 ...' format or similar.
                # Just handling common cases or errors='coerce'
                if 'pubDate' in df.columns:
                     df['date'] = pd.to_datetime(df['pubDate'], errors='coerce').dt.tz_localize(None)
                news_dfs.append(df)
        except Exception as e:
             print(f"Error loading {f}: {e}")

    if news_dfs:
        data['news'] = pd.concat(news_dfs, ignore_index=True)
        
    return data

def filter_data(data, keywords, start_date, end_date):
    """Filter data by keywords and date range."""
    filtered = {}
    start_ts = pd.Timestamp(start_date)
    end_ts = pd.Timestamp(end_date)
    
    for key, df in data.items():
        if df.empty:
            filtered[key] = df
            continue
            
        # Filter by keyword
        if keywords:
            mask_kw = df['keyword'].isin(keywords)
            df_sub = df[mask_kw].copy()
        else:
            df_sub = df.copy()
            
        # Filter by date
        if 'date' in df_sub.columns:
            # Drop rows with invalid dates
            df_sub = df_sub.dropna(subset=['date'])
            mask_date = (df_sub['date'] >= start_ts) & (df_sub['date'] <= end_ts)
            df_sub = df_sub[mask_date]
            
        filtered[key] = df_sub
        
    return filtered

# --- Sidebar ---
st.sidebar.title("🔍 설정 (Settings)")

# Load Data Trigger
if st.sidebar.button("데이터 다시 로드 (Reload Data)"):
    st.cache_data.clear()

data_all = load_all_data()

# Keyword Selection
available_keywords = []
if not data_all['trend'].empty:
    available_keywords = sorted(data_all['trend']['keyword'].unique())
elif not data_all['blog'].empty:
    available_keywords = sorted(data_all['blog']['keyword'].unique())

selected_keywords = st.sidebar.multiselect(
    "키워드 선택 (Keywords)", 
    options=available_keywords,
    default=available_keywords[:2] if available_keywords else None
)

# Date Range Selection
start_date = st.sidebar.date_input("시작일 (Start Date)", datetime(2024, 1, 1))
end_date = st.sidebar.date_input("종료일 (End Date)", datetime(2025, 12, 31))

# Filter Data
filtered_data = filter_data(data_all, selected_keywords, start_date, end_date)
df_trend = filtered_data['trend']
df_blog = filtered_data['blog']
df_news = filtered_data['news']

# --- Main Layout ---
st.title("📊 OTT 트렌드 분석 대시보드")

if not selected_keywords:
    st.warning("👈 사이드바에서 분석할 키워드를 선택해주세요.")
    st.stop()

tab1, tab2, tab3 = st.tabs(["📈 트렌드 비교 분석", "📰 검색어 기초 EDA", "💾 상세 데이터 조회"])

# --- Tab 1: Trend Analysis ---
with tab1:
    st.header("트렌드 비교 분석 (Trend Analysis)")
    
    if not df_trend.empty:
        # 1. Line Chart: Daily Trend
        st.subheader("1. 일간 검색어 트렌드 추이")
        fig_trend = px.line(
            df_trend, 
            x='date', 
            y='ratio', 
            color='keyword',
            title='키워드별 검색량 추이 (Search Trend Ratio)',
            markers=False
        )
        st.plotly_chart(fig_trend, use_container_width=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            # 2. Table: Trend Statistics
            st.subheader("2. 키워드별 트렌드 통계")
            stats = df_trend.groupby('keyword')['ratio'].agg(['mean', 'max', 'min', 'std']).reset_index()
            stats.columns = ['키워드', '평균', '최대', '최소', '표준편차']
            st.dataframe(stats, hide_index=True, use_container_width=True)
            
        with col2:
            # 3. Bar Chart: Monthly Average
            st.subheader("3. 월별 평균 검색량 비교")
            df_trend['month'] = df_trend['date'].dt.to_period('M').astype(str)
            monthly_avg = df_trend.groupby(['month', 'keyword'])['ratio'].mean().reset_index()
            fig_monthly = px.bar(
                monthly_avg, 
                x='month', 
                y='ratio', 
                color='keyword', 
                barmode='group',
                title='월별 검색량 평균'
            )
            st.plotly_chart(fig_monthly, use_container_width=True)
            
        # 4. Table: Top Spikes
        st.subheader("4. 검색량 급상승 날짜 TOP 5")
        top_spikes = df_trend.sort_values(by='ratio', ascending=False).groupby('keyword').head(5)
        top_spikes = top_spikes[['keyword', 'date', 'ratio']].sort_values(['keyword', 'ratio'], ascending=[True, False])
        top_spikes['date'] = top_spikes['date'].dt.strftime('%Y-%m-%d')
        st.dataframe(top_spikes, hide_index=True, use_container_width=True)
        
        # 5. Table: Day of Week Summary
        st.subheader("5. 요일별 평균 관심도")
        df_trend['day_name'] = df_trend['date'].dt.day_name()
        # Order days
        days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        df_trend['day_name'] = pd.Categorical(df_trend['day_name'], categories=days_order, ordered=True)
        dow_avg = df_trend.groupby(['day_name', 'keyword'], observed=True)['ratio'].mean().reset_index()
        dow_pivot = dow_avg.pivot(index='day_name', columns='keyword', values='ratio')
        st.dataframe(dow_pivot, use_container_width=True)

    else:
        st.info("선택한 기간 및 키워드에 대한 트렌드 데이터가 없습니다.")

# --- Tab 2: Content Analysis ---
with tab2:
    st.header("검색어 기초 EDA (Content Analysis)")
    
    # Pre-calculate counts
    b_count = 0 if df_blog.empty else len(df_blog)
    n_count = 0 if df_news.empty else len(df_news)
    
    if b_count == 0 and n_count == 0:
        st.info("선택한 키워드에 대한 블로그/뉴스 데이터가 없습니다.")
    else:
        col1, col2 = st.columns([1, 2])
        
        with col1:
             # Chart 3: Source Distribution
            st.subheader("1. 데이터 출처 분포")
            source_df = pd.DataFrame({
                'source': ['Blog', 'News'],
                'count': [b_count, n_count]
            })
            fig_pie = px.pie(source_df, values='count', names='source', title='블로그 vs 뉴스 수집 데이터 비율')
            st.plotly_chart(fig_pie, use_container_width=True)
            
        with col2:
            # Chart 4: Content Volume Over Time
            st.subheader("2. 일별 콘텐츠 발행량 추이")
            
            # Combine blog and news dates for histogram
            dates_blog = pd.DataFrame({'date': df_blog['date'], 'source': 'Blog', 'keyword': df_blog['keyword']}) if not df_blog.empty else pd.DataFrame()
            dates_news = pd.DataFrame({'date': df_news['date'], 'source': 'News', 'keyword': df_news['keyword']}) if not df_news.empty else pd.DataFrame()
            
            all_content = pd.concat([dates_blog, dates_news])
            
            if not all_content.empty:
                # Group by date and source
                daily_counts = all_content.groupby(['date', 'source']).size().reset_index(name='count')
                fig_vol = px.bar(
                    daily_counts, 
                    x='date', 
                    y='count', 
                    color='source', 
                    title='일별 콘텐츠 발행 건수',
                    barmode='stack'
                )
                st.plotly_chart(fig_vol, use_container_width=True)
        
        # Chart 5: Scatter Plot (Trend vs Volume)
        # Need to merge trend and content volume
        if not df_trend.empty and not all_content.empty:
            st.subheader("3. 트렌드 지수 vs 콘텐츠 발행량 상관관계")
            
            # Aggregate volume by date
            vol_by_date = all_content.groupby('date').size().reset_index(name='volume')
            
            # Aggregate trend ratio by date (average if multiple keywords selected, or just take one if single)
            # For scatter plot, it might be better to treat keywords separately, but let's aggregate for simplicity or filter to single keyword?
            # Let's group by date and keyword to see relationship per keyword
            
            vol_by_date_kw = all_content.groupby(['date', 'keyword']).size().reset_index(name='volume')
            trend_sub = df_trend[['date', 'keyword', 'ratio']]
            
            merged = pd.merge(trend_sub, vol_by_date_kw, on=['date', 'keyword'])
            
            if not merged.empty:
                fig_scatter = px.scatter(
                    merged, 
                    x='ratio', 
                    y='volume', 
                    color='keyword',
                    hover_data=['date'],
                    title='검색 트렌드(Ratio)와 콘텐츠 발행량(Volume) 관계'
                )
                st.plotly_chart(fig_scatter, use_container_width=True)
            else:
                st.caption("날짜가 일치하는 트렌드 및 콘텐츠 데이터가 부족하여 산점도를 그릴 수 없습니다.")
        
        st.divider()
        
        # Tables: Recent Items
        col_t1, col_t2 = st.columns(2)
        
        with col_t1:
            st.subheader("4. 최신 블로그 리뷰")
            if not df_blog.empty:
                display_cols = ['postdate', 'title', 'bloggername', 'link']
                # Rename for display if columns exist
                disp_df = df_blog.copy()
                if 'postdate' in disp_df.columns: disp_df['Date'] = disp_df['postdate']
                if 'title' in disp_df.columns: disp_df['Title'] = disp_df['title'] # Using a markdown link would be better but st.dataframe has limited support.
                
                st.dataframe(
                    disp_df[['Date', 'Title', 'bloggername']].head(10), 
                    hide_index=True, 
                    use_container_width=True
                )
            else:
                st.caption("표시할 블로그 데이터가 없습니다.")
                
        with col_t2:
            st.subheader("5. 최신 뉴스 이슈")
            if not df_news.empty:
                 # pubDate, title, originallink, link, description
                disp_df = df_news.copy()
                if 'pubDate' in disp_df.columns: disp_df['Date'] = disp_df['pubDate']
                if 'title' in disp_df.columns: disp_df['Title'] = disp_df['title']
                
                st.dataframe(
                    disp_df[['Date', 'Title']].head(10), 
                    hide_index=True, 
                    use_container_width=True
                )
            else:
                st.caption("표시할 뉴스 데이터가 없습니다.")

# --- Tab 3: Raw Data ---
with tab3:
    st.header("상세 데이터 조회 (Raw Data)")
    
    st.subheader("데이터랩 트렌드 (Trends)")
    st.dataframe(df_trend, use_container_width=True)
    
    st.subheader("블로그 리뷰 (Blogs)")
    st.dataframe(df_blog, use_container_width=True)
    
    st.subheader("뉴스 이슈 (News)")
    st.dataframe(df_news, use_container_width=True)
