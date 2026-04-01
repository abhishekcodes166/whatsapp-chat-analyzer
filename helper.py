from urlextract import URLExtract

def fetch_stats(selected_user, df):

    # filter dataframe by user
    if selected_user != 'Overall':
        df = df[df['user'] == selected_user]

    # total messages
    num_messages = df.shape[0]

    # total words
    num_of_words = df['message_only'].dropna().str.split().str.len().sum()

    # media counts (based on your message_only text)
    num_images = df[df['message_only'].str.contains('image omitted', case=False, na=False)].shape[0]
    num_videos = df[df['message_only'].str.contains('video omitted', case=False, na=False)].shape[0]
    num_stickers = df[df['message_only'].str.contains('sticker omitted', case=False, na=False)].shape[0]
    num_gifs = df[df['message_only'].str.contains('gif omitted', case=False, na=False)].shape[0]
    num_audios = df[df['message_only'].str.contains('audio omitted', case=False, na=False)].shape[0]
    num_documents = df[df['message_only'].str.contains('document omitted', case=False, na=False)].shape[0]
    total_media = num_audios + num_documents + num_gifs + num_images + num_stickers + num_videos
    links = []
    url_extractor = URLExtract()    
    for message in df['message_only']:
        links.extend(url_extractor.find_urls(message))
    links = len(links)      
    return (
        num_messages,
        num_of_words,
        total_media,
        links      
    )

def find_busiest_user(df):
    return df['user'].value_counts().head()    

