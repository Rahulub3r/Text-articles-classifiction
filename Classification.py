import requests
import urllib2
from bs4 import BeautifulSoup
from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.corpus import stopwords
from collections import defaultdict
from string import punctuation
from heapq import nlargest
from math import log
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans


def getWashPostText(url,token):
    try:
        page = urllib2.urlopen(url).read().decode('utf8')
    except:
        # if unable to download the URL, return title = None, article = None
        return (None,None)
    soup = BeautifulSoup(page)
    if soup is None:
        return (None,None)
    # If we are here, it means the error checks were successful, we were
    # able to parse the page
    text = ""
    if soup.find_all(token) is not None:
        text = ''.join(map(lambda p: p.text, soup.find_all(token)))
        soup2 = BeautifulSoup(text)
        if soup2.find_all('p')!=[]:
            text = ''.join(map(lambda p: p.text, soup2.find_all('p')))
    return text, soup.title.text

def getNYTText(url,token):
    response = requests.get(url)
    soup = BeautifulSoup(response.content)
    page = str(soup)
    title = soup.find('title').text
    mydivs = soup.findAll("p", {"class":"story-body-text story-content"})
    text = ''.join(map(lambda p:p.text, mydivs))
    return text, title
   
def scrapeSource(url, magicFrag='2015',scraperFunction=getNYTText,token='None'):
    urlBodies = {}
    request = urllib2.Request(url, headers={'User-Agent' : "foobar"})
    response = urllib2.urlopen(request)
    soup = BeautifulSoup(response)
    numErrors = 0
    for a in soup.findAll('a'):
        try:
            url = a['href']
            if( (url not in urlBodies) and 
               ((magicFrag is not None and magicFrag in url) 
               or magicFrag is None)):
                body = scraperFunction(url,token)
                if body and len(body) > 0:
                    urlBodies[url] = body
                print url
        except:
            numErrors += 1
    return urlBodies

class FrequencySummarizer:
    def __init__(self,min_cut=0.1,max_cut=0.9):
        self._min_cut = min_cut
        self._max_cut = max_cut
        self._stopwords = set(stopwords.words('english') +
                              list(punctuation) +
                              [u"'s",'"'])
    
    def _compute_frequencies(self,word_sent,customStopWords=None):
        freq = defaultdict(int)
        if customStopWords is None:
            stopwords = set(self._stopwords)
        else:
            stopwords = set(customStopWords).union(self._stopwords)
        for sentence in word_sent:
            for word in sentence:
                if word not in stopwords:
                    freq[word] += 1
        m = float(max(freq.values()))
        for word in freq.keys():
            freq[word] = freq[word]/m
            if freq[word] >= self._max_cut or freq[word] <= self._min_cut:
                del freq[word]
        return freq
    
    def extractFeatures(self,article,n,customStopWords=None):
        # The article is passed in as a tuple (text, title)
        text = article[0]
        # extract the text
        title = article[1]
        # extract the title
        sentences = sent_tokenize(text)
        # split the text into sentences
        word_sent = [word_tokenize(s.lower()) for s in sentences]
        self._freq = self._compute_frequencies(word_sent,customStopWords)
        if n < 0:
            return nlargest(len(self._freq_keys()),self._freq,key=self._freq.get)
        else:
            return nlargest(n,self._freq,key=self._freq.get)
           
    def extractRawFrequencies(self, article):
        text = article[0]
        title = article[1]
        sentences = sent_tokenize(text)
        word_sent = [word_tokenize(s.lower()) for s in sentences]
        freq = defaultdict(int)
        for s in word_sent:
            for word in s:
                if word not in self._stopwords:
                    freq[word] += 1
        return freq
    
    def summarize(self, article,n):
        text = article[0]
        title = article[1]
        sentences = sent_tokenize(text)
        word_sent = [word_tokenize(s.lower()) for s in sentences]
        self._freq = self._compute_frequencies(word_sent)
        ranking = defaultdict(int)
        for i,sentence in enumerate(word_sent):
            for word in sentence:
                if word in self._freq:
                    ranking[i] += self._freq[word]
        sentences_index = nlargest(n,ranking,key=ranking.get)

        return [sentences[j] for j in sentences_index]


urlWashingtonPostNonTech = "https://www.washingtonpost.com/sports"
urlNewYorkTimesNonTech = "https://www.nytimes.com/pages/sports/index.html"
urlWashingtonPostTech = "https://www.washingtonpost.com/business/technology"
urlNewYorkTimesTech = "http://www.nytimes.com/pages/technology/index.html"

washingtonPostTechArticles = scrapeSource(urlWashingtonPostTech,
                                          '2016',
                                         getWashPostText,
                                         'article') 
washingtonPostNonTechArticles = scrapeSource(urlWashingtonPostNonTech,
                                          '2016',
                                         getWashPostText,
                                         'article')
                
                
newYorkTimesTechArticles = scrapeSource(urlNewYorkTimesTech,
                                       '2016',
                                       getNYTText,
                                       None)
newYorkTimesNonTechArticles = scrapeSource(urlNewYorkTimesNonTech,
                                       '2016',
                                       getNYTText,
                                       None)

articleSummaries = {}
for techUrlDictionary in [newYorkTimesTechArticles, washingtonPostTechArticles]:
    for articleUrl in techUrlDictionary:
        if techUrlDictionary[articleUrl][0] is not None:
            if len(techUrlDictionary[articleUrl][0]) > 0:
                fs = FrequencySummarizer()
                summary = fs.extractFeatures(techUrlDictionary[articleUrl],25)
                articleSummaries[articleUrl] = {'feature-vector': summary,
                                               'label': 'Tech'}
for nontechUrlDictionary in [newYorkTimesNonTechArticles, washingtonPostNonTechArticles]:
    for articleUrl in nontechUrlDictionary:
        if nontechUrlDictionary[articleUrl][0] is not None:
            if len(nontechUrlDictionary[articleUrl][0]) > 0:
                fs = FrequencySummarizer()
                summary = fs.extractFeatures(nontechUrlDictionary[articleUrl],25)
                articleSummaries[articleUrl] = {'feature-vector': summary,
                                               'label': 'Non-Tech'}

def getDoxyDonkeyText(testUrl,token):
    response = requests.get(testUrl)
    soup = BeautifulSoup(response.content)
    page = str(soup)
    title = soup.find("title").text
    mydivs = soup.findAll("div", {"class":token})
    text = ''.join(map(lambda p:p.text,mydivs))
    return text,title

testUrl = "http://doxydonkey.blogspot.in"
testArticle = getDoxyDonkeyText(testUrl,"post-body")

fs = FrequencySummarizer()
testArticleSummary = fs.extractFeatures(testArticle, 25)

similarities = {}
for articleUrl in articleSummaries:
    oneArticleSummary = articleSummaries[articleUrl]['feature-vector']
    similarities[articleUrl] = len(set(testArticleSummary).intersection(set(oneArticleSummary)))

labels = defaultdict(int)    
knn = nlargest(5, similarities, key=similarities.get)
for oneNeighbor in knn:
    labels[articleSummaries[oneNeighbor]['label']] += 1

nlargest(1,labels,key=labels.get)


cumulativeRawFrequencies = {'Tech':defaultdict(int),'Non-Tech':defaultdict(int)}
trainingData = {'Tech':newYorkTimesTechArticles,'Non-Tech':newYorkTimesNonTechArticles}
for label in trainingData:
    for articleUrl in trainingData[label]:
        if len(trainingData[label][articleUrl][0]) > 0:
            fs = FrequencySummarizer()
            rawFrequencies = fs.extractRawFrequencies(trainingData[label][articleUrl])
            for word in rawFrequencies:
                cumulativeRawFrequencies[label][word] += rawFrequencies[word]


techiness = 1.0
nontechiness = 1.0
for word in testArticleSummary: 
    if word in cumulativeRawFrequencies['Tech']:
        techiness *= 1e3*cumulativeRawFrequencies['Tech'][word] / float(sum(cumulativeRawFrequencies['Tech'].values()))
        
    else:
        techiness /= 1e3
        
    if word in cumulativeRawFrequencies['Non-Tech']:
        nontechiness *= 1e3*cumulativeRawFrequencies['Non-Tech'][word] / float(sum(cumulativeRawFrequencies['Non-Tech'].values()))
    else:
        nontechiness /= 1e3

techiness *= float(sum(cumulativeRawFrequencies['Tech'].values())) / (float(sum(cumulativeRawFrequencies['Tech'].values())) + float(sum(cumulativeRawFrequencies['Non-Tech'].values())))
nontechiness *= float(sum(cumulativeRawFrequencies['Non-Tech'].values())) / (float(sum(cumulativeRawFrequencies['Tech'].values())) + float(sum(cumulativeRawFrequencies['Non-Tech'].values())))
if techiness > nontechiness:
    label = 'Tech'
else:
    label = 'Non-Tech'
print label, techiness, nontechiness

def getAllDoxyDonkeyPosts(url,links):
    request = urllib2.Request(url)
    response = urllib2.urlopen(request)
    soup = BeautifulSoup(response)
    for a in soup.findAll('a'):
        try:
            url = a['href']
            title = a['title']
            if title == "Older Posts":
                print title, url
                links.append(url)
                getAllDoxyDonkeyPosts(url,links)
        except:
            title = ""
    return

blogUrl = "http://doxydonkey.blogspot.in"
links = []
getAllDoxyDonkeyPosts(blogUrl,links)
doxyDonkeyPosts = {}
for link in links:
    doxyDonkeyPosts[link] = getDoxyDonkeyText(link,'post-body')


documentCorpus = []
for onePost in doxyDonkeyPosts.values():
    documentCorpus.append(onePost[0])

vectorizer = TfidfVectorizer(max_df=0.5,min_df=2,stop_words='english')
X = vectorizer.fit_transform(documentCorpus)
km = KMeans(n_clusters = 5, init = 'k-means++', max_iter = 100, n_init = 1, verbose = True)
km.fit(X)

keywords = {}
for i,cluster in enumerate(km.labels_):
    oneDocument = documentCorpus[i]
    fs = FrequencySummarizer()
    summary = fs.extractFeatures((oneDocument,""),
                                100,
                                [u"according",u"also",u"billion",u"like",u"new", u"one",u"year",u"first",u"last"])
    if cluster not in keywords:
        keywords[cluster] = set(summary)
    else:
        keywords[cluster] = keywords[cluster].intersection(set(summary))