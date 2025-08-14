#!/usr/bin/env python3
"""
Keyword Extraction Service for RAG Chatbot
Uses spaCy + TF-IDF approach optimized for chunk-level processing
"""

import re
import logging
from typing import List, Dict, Optional
from collections import Counter
import numpy as np

try:
    import spacy
    from sklearn.feature_extraction.text import TfidfVectorizer
    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False

logger = logging.getLogger(__name__)

class KeywordExtractor:
    """
    spaCy + TF-IDF based keyword extractor optimized for document chunks
    """
    
    def __init__(self):
        self.nlp = None
        self.vectorizer = None
        self.spacy_available = SPACY_AVAILABLE  # Store as instance variable
        
        # Initialize spaCy if available
        if self.spacy_available:
            try:
                self.nlp = spacy.load("en_core_web_sm")
                logger.info("✅ spaCy model loaded successfully")
            except OSError:
                logger.warning("⚠️ spaCy model 'en_core_web_sm' not found. Install with: python -m spacy download en_core_web_sm")
                self.spacy_available = False
        
        if not self.spacy_available:
            logger.warning("⚠️ spaCy not available, falling back to rule-based extraction")
        
        # Technical patterns for fallback
        self.technical_patterns = {
            'camel_case': re.compile(r'\b[a-z]+(?:[A-Z][a-z]*)+\b'),
            'pascal_case': re.compile(r'\b[A-Z][a-z]*(?:[A-Z][a-z]*)+\b'),
            'snake_case': re.compile(r'\b[a-z]+(?:_[a-z]+)+\b'),
            'acronyms': re.compile(r'\b[A-Z]{2,}\b'),
            'function_calls': re.compile(r'\b[a-zA-Z_][a-zA-Z0-9_]*\([^)]*\)'),
        }
        
        # Common stop words
        self.stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
            'should', 'may', 'might', 'can', 'shall', 'this', 'that', 'these',
            'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him',
            'her', 'us', 'them', 'my', 'your', 'his', 'her', 'its', 'our', 'their'
        }

    def extract_keywords(self, text: str, max_keywords: int = 15, 
                        document_context: Optional[str] = None,
                        chunk_summary: Optional[str] = None) -> List[str]:
        """
        Extract keywords using your spaCy + TF-IDF approach, enhanced for chunks
        
        Args:
            text: The chunk text to extract keywords from
            max_keywords: Maximum number of keywords to return
            document_context: Full document text for better TF-IDF context
            chunk_summary: Summary of the chunk for additional context
            
        Returns:
            List of extracted keywords, ranked by importance
        """
        try:
            if self.spacy_available and self.nlp:
                logger.info(f"Extracting keywords with spaCy + TF-IDF for text with length: {len(text)}")
                return self._extract_with_spacy_tfidf(text, max_keywords, document_context , chunk_summary)
            else:
                logger.info(f"Extracting keywords with fallback for text with length: {len(text)}")
                return self._extract_fallback(text, max_keywords)
                
        except Exception as e:
            logger.error(f"Keyword extraction failed: {e}") 
            logger.error(f"Extracting keywords with fallback for text with length: {len(text)}")
            return self._extract_fallback(text, max_keywords)

    def _extract_with_spacy_tfidf(self, text: str, max_keywords: int, 
                                 document_context: Optional[str] = None,
                                 chunk_summary: Optional[str] = None) -> List[str]:
        """Enhanced version of your spaCy + TF-IDF approach"""
        
        # Combine text sources for analysis
        analysis_texts = [text]
        if chunk_summary:
            analysis_texts.append(chunk_summary)
        if document_context:
            # Use document context but give more weight to current chunk
            analysis_texts.extend([text, text])  # Triple weight for current chunk
        
        all_nouns = []
        all_technical_terms = []
        
        for txt in analysis_texts:
            doc = self.nlp(txt)
            
            # Extract nouns and proper nouns (your approach)
            nouns = [token.lemma_.lower() for token in doc
                    if (token.pos_ in ["NOUN", "PROPN"] and 
                        not token.is_stop and 
                        len(token.text) > 2 and
                        token.text.lower() not in self.stop_words)]
            all_nouns.extend(nouns)
            
            # Also extract technical terms that spaCy might miss
            technical_terms = self._extract_technical_terms(txt)
            all_technical_terms.extend(technical_terms)
        
        # Combine nouns and technical terms
        combined_terms = all_nouns + all_technical_terms
        
        if not combined_terms:
            return self._extract_fallback(text, max_keywords)
        
        # Create documents for TF-IDF (your approach, but enhanced)
        nouns_text = " ".join(combined_terms)
        
        # If we have document context, create multiple documents for better TF-IDF
        if document_context and len(analysis_texts) > 1:
            documents = []
            for txt in analysis_texts:
                doc = self.nlp(txt)
                doc_nouns = [token.lemma_.lower() for token in doc
                           if token.pos_ in ["NOUN", "PROPN"] and not token.is_stop]
                if doc_nouns:
                    documents.append(" ".join(doc_nouns))
            
            if len(documents) > 1:
                # Fit TF-IDF on multiple documents for better scoring
                vectorizer = TfidfVectorizer(max_features=1000, ngram_range=(1, 2))
                tfidf_matrix = vectorizer.fit_transform(documents)
                
                # Get scores for the main chunk (first document)
                scores = tfidf_matrix[0].toarray()[0]
                vocab = vectorizer.get_feature_names_out()
                
                # Get top keywords
                return_number = self._compute_num_of_items_to_return(text, max_keywords)
                top_indices = scores.argsort()[::-1][:return_number]
                top_keywords = [vocab[i] for i in top_indices if scores[i] > 0]
                
                return top_keywords
        
        # Fallback to single document TF-IDF
        if combined_terms:
            vectorizer = TfidfVectorizer(ngram_range=(1, 2))
            try:
                tfidf = vectorizer.fit_transform([nouns_text])
                scores = tfidf.toarray()[0]
                vocab = vectorizer.get_feature_names_out()
                
                return_number = self._compute_num_of_items_to_return(text, max_keywords)
                top_keywords = [vocab[i] for i in scores.argsort()[::-1][:return_number]]
                
                return [kw for kw in top_keywords if len(kw.strip()) > 1]
            except:
                pass
        
        # Final fallback
        return self._extract_fallback(text, max_keywords)

    def _extract_technical_terms(self, text: str) -> List[str]:
        """Extract technical terms that spaCy might miss"""
        technical_terms = []
        
        for pattern_name, pattern in self.technical_patterns.items():
            matches = pattern.findall(text)
            if pattern_name == 'function_calls':
                # Extract function names
                func_names = [match.split('(')[0].lower() for match in matches]
                technical_terms.extend(func_names)
            else:
                technical_terms.extend([match.lower() for match in matches])
        
        return technical_terms

    def _compute_num_of_items_to_return(self, text: str, max_keywords: int) -> int:
        """Enhanced version of your dynamic sizing logic"""
        # Count words in the text
        words = text.split()
        num_words = len(words)
        
        # Your 0.9% rule, but with some bounds
        percentage_based = int(num_words * 0.009)
        
        # Apply reasonable bounds
        if num_words < 50:
            return min(3, max_keywords)
        elif num_words < 200:
            return min(max(percentage_based, 5), max_keywords)
        else:
            return min(max(percentage_based, 8), max_keywords)

    def _extract_fallback(self, text: str, max_keywords: int) -> List[str]:
        """Simple fallback when spaCy is not available"""
        # Simple frequency-based extraction
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
        filtered_words = [w for w in words if w not in self.stop_words]
        
        # Add technical terms
        technical_terms = self._extract_technical_terms(text)
        filtered_words.extend(technical_terms)
        
        # Count frequencies
        word_counts = Counter(filtered_words)
        return_number = min(max_keywords, len(word_counts))
        
        return [word for word, _ in word_counts.most_common(return_number)]

    def extract_keywords_batch(self, chunks: List[str], max_keywords: int = 15, 
                             document_context: Optional[str] = None) -> List[List[str]]:
        """
        Extract keywords for multiple chunks with optimized shared context processing.
        
        This method processes the document context once and reuses TF-IDF calculations
        for all chunks, significantly improving performance.
        
        Args:
            chunks: List of chunk texts to extract keywords from
            max_keywords: Maximum number of keywords per chunk
            document_context: Full document text for TF-IDF context (optional)
            
        Returns:
            List of keyword lists, one for each chunk
        """
        if not chunks:
            return []
        
        # If no document context provided, use all chunks as context
        if document_context is None:
            document_context = "\n".join(chunks)
        
        try:
            if self.spacy_available and self.nlp:
                logger.info(f"Batch extracting keywords with spaCy + TF-IDF for {len(chunks)} chunks")
                return self._extract_batch_with_spacy_tfidf(chunks, max_keywords, document_context)
            else:
                logger.info(f"Batch extracting keywords with fallback for {len(chunks)} chunks")
                return self._extract_batch_fallback(chunks, max_keywords)
                
        except Exception as e:
            logger.error(f"Batch keyword extraction failed: {e}")
            logger.info(f"Falling back to individual extraction for {len(chunks)} chunks")
            # Fallback to individual extraction without context for speed
            return [self._extract_fallback(chunk, max_keywords) for chunk in chunks]

    def _extract_batch_with_spacy_tfidf(self, chunks: List[str], max_keywords: int, 
                                      document_context: str) -> List[List[str]]:
        """
        Optimized batch processing with spaCy + TF-IDF.
        Processes document context once and reuses TF-IDF model for all chunks.
        """
        # Step 1: Process document context once to build vocabulary
        logger.info(f"Creating context nouns from document context, to feed to TF-IDF model")
        doc_context = self.nlp(document_context)
        context_nouns = [token.lemma_.lower() for token in doc_context
                        if (token.pos_ in ["NOUN", "PROPN"] and 
                            not token.is_stop and 
                            len(token.text) > 2 and
                            token.text.lower() not in self.stop_words)]
        
        # Step 2: Process all chunks to build documents for TF-IDF
        chunk_documents = []
        chunk_technical_terms = []
        
        for chunk in chunks:
            logger.info(f"Creating context nouns from chunk with length {len(chunk)}, to feed to TF-IDF model")
            doc = self.nlp(chunk)
            chunk_nouns = [token.lemma_.lower() for token in doc
                          if (token.pos_ in ["NOUN", "PROPN"] and 
                              not token.is_stop and 
                              len(token.text) > 2 and
                              token.text.lower() not in self.stop_words)]
            
            # Add technical terms
            technical_terms = self._extract_technical_terms(chunk)
            chunk_technical_terms.append(technical_terms)
            
            # Combine nouns and technical terms for this chunk
            all_terms = chunk_nouns + technical_terms
            chunk_documents.append(" ".join(all_terms) if all_terms else "")
        
        # Step 3: Build TF-IDF model once for all documents
        if not any(chunk_documents):
            return [self._extract_fallback(chunk, max_keywords) for chunk in chunks]
        
        try:
            # Create document collection: context + all chunks
            all_documents = [" ".join(context_nouns)] + chunk_documents
            logger.info(f"All documents length: {len(all_documents)}")
            
            # Build TF-IDF vectorizer once
            vectorizer = TfidfVectorizer(max_features=1000, ngram_range=(1, 2))
            tfidf_matrix = vectorizer.fit_transform(all_documents)
            logger.info(f"TF-IDF matrix shape: {tfidf_matrix.shape}")
            vocab = vectorizer.get_feature_names_out()
            
            # Step 4: Extract keywords for each chunk using shared TF-IDF model
            results = []
            for i, chunk in enumerate(chunks):
                # Get TF-IDF scores for this chunk (index i+1, since context is at index 0)
                chunk_idx = i + 1
                if chunk_idx < tfidf_matrix.shape[0]:
                    scores = tfidf_matrix[chunk_idx].toarray()[0]
                    
                    # Get top keywords for this chunk
                    return_number = self._compute_num_of_items_to_return(chunk, max_keywords)
                    top_indices = scores.argsort()[::-1][:return_number]
                    top_keywords = [vocab[idx] for idx in top_indices if scores[idx] > 0]
                    
                    # Add technical terms that might not be in TF-IDF vocab
                    technical_kw = chunk_technical_terms[i][:max_keywords//3]
                    combined_keywords = list(dict.fromkeys(top_keywords + technical_kw))[:return_number]
                    
                    results.append(combined_keywords)
                else:
                    # Fallback for this chunk
                    results.append(self._extract_fallback(chunk, max_keywords))
            
            return results
            
        except Exception as e:
            logger.error(f"Error in batch TF-IDF processing: {e}")
            return [self._extract_fallback(chunk, max_keywords) for chunk in chunks]

    def _extract_batch_fallback(self, chunks: List[str], max_keywords: int) -> List[List[str]]:
        """Fallback batch processing when spaCy is not available"""
        results = []
        for chunk in chunks:
            results.append(self._extract_fallback(chunk, max_keywords))
        return results

    def get_extraction_stats(self, text: str, keywords: List[str]) -> Dict:
        """Get statistics about the extraction process"""
        return {
            'text_length': len(text),
            'word_count': len(text.split()),
            'keywords_extracted': len(keywords),
            'keyword_density': len(keywords) / len(text.split()) if text.split() else 0,
            'spacy_available': self.spacy_available,
            'extraction_method': 'spacy_tfidf' if self.spacy_available else 'fallback'
        }