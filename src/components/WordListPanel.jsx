import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './WordListPanel.scss';

const WordListPanel = () => {
  const [wordlists, setWordlists] = useState([]);
  const [categories, setCategories] = useState({});
  const [tags, setTags] = useState({});
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [selectedWordlist, setSelectedWordlist] = useState(null);
  const [wordlistContent, setWordlistContent] = useState(null);
  const [wordlistStats, setWordlistStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showStats, setShowStats] = useState(false);
  const [editMode, setEditMode] = useState(false);
  const [newWords, setNewWords] = useState('');
  const [showUpload, setShowUpload] = useState(false);
  const [uploadName, setUploadName] = useState('');
  const [uploadFile, setUploadFile] = useState(null);
  const [uploadError, setUploadError] = useState('');
  const [error, setError] = useState(null);
  const [operationStatus, setOperationStatus] = useState(null);

  // Load wordlists on mount
  useEffect(() => {
    loadWordlists();
  }, []);

  const loadWordlists = async () => {
    try {
      setError(null);
      const response = await axios.get('/api/wordlists');
      setWordlists(response.data.wordlists);
      setCategories(response.data.categories);
      setTags(response.data.tags);
      setLoading(false);
    } catch (error) {
      console.error('Failed to load wordlists:', error);
      setError('Failed to load wordlists. Please refresh the page.');
      setLoading(false);
    }
  };

  const loadWordlist = async (key) => {
    try {
      setLoading(true);
      setError(null);
      const response = await axios.get(`/api/wordlists/${key}`, {
        params: { stats: showStats }
      });
      setWordlistContent(response.data);
      setWordlistStats(response.data.stats);
      setSelectedWordlist(key);
      setLoading(false);
    } catch (error) {
      console.error('Failed to load wordlist:', error);
      setError(`Failed to load wordlist "${key}". Please try again.`);
      setLoading(false);
    }
  };

  const handleCategoryChange = (category) => {
    setSelectedCategory(category);
    setSelectedWordlist(null);
    setWordlistContent(null);
  };

  const filteredWordlists = selectedCategory === 'all'
    ? wordlists
    : wordlists.filter(wl => wl.category === selectedCategory);

  const handleAddWords = async () => {
    if (!newWords.trim() || !selectedWordlist) return;

    const wordsToAdd = newWords.split('\n')
      .map(w => w.trim().toUpperCase())
      .filter(w => w && !w.startsWith('#'));

    try {
      setError(null);
      setOperationStatus('Adding words...');
      await axios.put(`/api/wordlists/${selectedWordlist}`, {
        add_words: wordsToAdd
      });
      await loadWordlist(selectedWordlist);
      setNewWords('');
      setEditMode(false);
      setOperationStatus(`Successfully added ${wordsToAdd.length} word(s)!`);
      setTimeout(() => setOperationStatus(null), 3000);
    } catch (error) {
      console.error('Failed to add words:', error);
      setError(error.response?.data?.error || 'Failed to add words. Please try again.');
      setOperationStatus(null);
    }
  };

  const handleDeleteWordlist = async (key) => {
    if (!window.confirm(`Delete wordlist "${key}"? This cannot be undone.`)) return;

    try {
      setError(null);
      setOperationStatus('Deleting wordlist...');
      await axios.delete(`/api/wordlists/${key}`);
      await loadWordlists();
      if (selectedWordlist === key) {
        setSelectedWordlist(null);
        setWordlistContent(null);
      }
      setOperationStatus(`Successfully deleted "${key}"!`);
      setTimeout(() => setOperationStatus(null), 3000);
    } catch (error) {
      console.error('Failed to delete wordlist:', error);
      setError(error.response?.data?.error || 'Failed to delete wordlist. Please try again.');
      setOperationStatus(null);
    }
  };

  const handleFileSelect = (event) => {
    const file = event.target.files[0];
    if (!file) return;

    // Validate file type
    if (!file.name.endsWith('.txt')) {
      setUploadError('Please select a .txt file');
      return;
    }

    // Validate file size (max 10MB)
    if (file.size > 10 * 1024 * 1024) {
      setUploadError('File size must be less than 10MB');
      return;
    }

    setUploadFile(file);
    setUploadError('');

    // Auto-populate name from filename (without .txt extension)
    if (!uploadName) {
      setUploadName(file.name.replace('.txt', ''));
    }
  };

  const handleUpload = async () => {
    if (!uploadFile || !uploadName.trim()) {
      setUploadError('Please provide a name and select a file');
      return;
    }

    try {
      setLoading(true);
      setUploadError('');

      // Read file content
      const content = await uploadFile.text();

      // Send to backend
      const response = await axios.post('/api/wordlists/import', {
        name: uploadName.trim(),
        content: content,
        category: 'custom',
        metadata: {
          description: `Uploaded from ${uploadFile.name}`,
          tags: ['custom', 'uploaded']
        }
      });

      // Refresh wordlists
      await loadWordlists();

      // Reset form
      setUploadFile(null);
      setUploadName('');
      setShowUpload(false);
      setLoading(false);

      // Auto-select the new wordlist
      const newKey = response.data.name;
      await loadWordlist(newKey);

    } catch (error) {
      console.error('Failed to upload wordlist:', error);
      setUploadError(error.response?.data?.error || 'Failed to upload wordlist');
      setLoading(false);
    }
  };

  return (
    <div className="wordlist-panel">
      <div className="panel-header">
        <h2>Word List Management</h2>
        <button
          className="upload-btn-header"
          onClick={() => setShowUpload(!showUpload)}
        >
          {showUpload ? 'Cancel Upload' : '📤 Upload Wordlist'}
        </button>
      </div>

      {error && (
        <div className="error-banner">
          <strong>Error:</strong> {error}
          <button className="dismiss-btn" onClick={() => setError(null)}>×</button>
        </div>
      )}

      {operationStatus && (
        <div className="status-banner">
          {operationStatus}
        </div>
      )}

      {showUpload && (
        <div className="upload-section">
          <h3>Upload Wordlist</h3>
          <div className="upload-form">
            <div className="form-group">
              <label>Wordlist Name:</label>
              <input
                type="text"
                value={uploadName}
                onChange={(e) => setUploadName(e.target.value)}
                placeholder="Enter a name for this wordlist"
              />
            </div>

            <div className="form-group">
              <label>Select File (.txt):</label>
              <input
                type="file"
                accept=".txt"
                onChange={handleFileSelect}
              />
              {uploadFile && (
                <div className="file-info">
                  Selected: {uploadFile.name} ({(uploadFile.size / 1024).toFixed(1)} KB)
                </div>
              )}
            </div>

            {uploadError && (
              <div className="upload-error">{uploadError}</div>
            )}

            <div className="upload-actions">
              <button
                className="upload-btn"
                onClick={handleUpload}
                disabled={!uploadFile || !uploadName.trim() || loading}
              >
                {loading ? 'Uploading...' : 'Upload'}
              </button>
              <button
                className="cancel-btn"
                onClick={() => {
                  setShowUpload(false);
                  setUploadFile(null);
                  setUploadName('');
                  setUploadError('');
                }}
              >
                Cancel
              </button>
            </div>

            <div className="upload-help">
              <p><strong>File Format:</strong> Plain text file with one word per line</p>
              <p><strong>Example:</strong></p>
              <pre>APPLE{'\n'}BANANA{'\n'}CHERRY</pre>
            </div>
          </div>
        </div>
      )}

      <div className="panel-layout">
        {/* Left sidebar - Categories and wordlists */}
        <div className="sidebar">
          <div className="categories">
            <h3>Categories</h3>
            <div className="category-list">
              <button
                className={`category-btn ${selectedCategory === 'all' ? 'active' : ''}`}
                onClick={() => handleCategoryChange('all')}
              >
                📋 All Wordlists
              </button>
              {Object.entries(categories).map(([key, cat]) => (
                <button
                  key={key}
                  className={`category-btn ${selectedCategory === key ? 'active' : ''}`}
                  onClick={() => handleCategoryChange(key)}
                >
                  {cat.icon} {cat.name}
                </button>
              ))}
            </div>
          </div>

          <div className="wordlist-list">
            <h3>
              {selectedCategory === 'all' ? 'All Wordlists' : categories[selectedCategory]?.name}
              <span className="count">({filteredWordlists.length})</span>
            </h3>
            {filteredWordlists.map(wl => (
              <div
                key={wl.key}
                className={`wordlist-item ${selectedWordlist === wl.key ? 'selected' : ''}`}
                onClick={() => loadWordlist(wl.key)}
              >
                <div className="wordlist-name">{wl.name}</div>
                <div className="wordlist-meta">
                  {wl.word_count && <span className="word-count">{wl.word_count} words</span>}
                  {wl.difficulty && <span className={`difficulty ${wl.difficulty}`}>{wl.difficulty}</span>}
                </div>
                {wl.tags && (
                  <div className="wordlist-tags">
                    {wl.tags.slice(0, 3).map(tag => (
                      <span key={tag} className="tag" style={{ backgroundColor: tags[tag]?.color }}>
                        {tag}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Right content - Selected wordlist details */}
        <div className="content">
          {loading ? (
            <div className="loading">
              <div className="spinner"></div>
              <p>Loading...</p>
            </div>
          ) : wordlistContent ? (
            <div className="wordlist-content">
              <div className="content-header">
                <h3>{wordlistContent.metadata.name}</h3>
                <div className="actions">
                  <button
                    className="stats-btn"
                    onClick={() => {
                      setShowStats(!showStats);
                      loadWordlist(selectedWordlist);
                    }}
                  >
                    {showStats ? 'Hide Stats' : 'Show Stats'}
                  </button>
                  <button
                    className="edit-btn"
                    onClick={() => setEditMode(!editMode)}
                  >
                    {editMode ? 'Cancel Edit' : 'Add Words'}
                  </button>
                  {wordlistContent.metadata.category === 'custom' && (
                    <button
                      className="delete-btn"
                      onClick={() => handleDeleteWordlist(selectedWordlist)}
                    >
                      Delete
                    </button>
                  )}
                </div>
              </div>

              <div className="metadata">
                <p className="description">{wordlistContent.metadata.description}</p>
                <div className="meta-info">
                  <span>Category: {wordlistContent.metadata.category}</span>
                  <span>Words: {wordlistContent.words.length}</span>
                  {wordlistContent.metadata.difficulty && (
                    <span>Difficulty: {wordlistContent.metadata.difficulty}</span>
                  )}
                </div>
              </div>

              {editMode && (
                <div className="edit-section">
                  <h4>Add Words</h4>
                  <textarea
                    value={newWords}
                    onChange={(e) => setNewWords(e.target.value)}
                    placeholder="Enter words (one per line)"
                    rows={5}
                  />
                  <button className="save-btn" onClick={handleAddWords}>
                    Add Words to List
                  </button>
                </div>
              )}

              {wordlistStats && showStats && (
                <div className="stats-section">
                  <h4>Statistics</h4>
                  <div className="stats-grid">
                    <div className="stat">
                      <label>Total Words:</label>
                      <span>{wordlistStats.total_words}</span>
                    </div>
                    <div className="stat">
                      <label>Average Length:</label>
                      <span>{wordlistStats.average_length.toFixed(1)} letters</span>
                    </div>
                    <div className="stat">
                      <label>Unique Letters:</label>
                      <span>{wordlistStats.unique_letters}</span>
                    </div>
                  </div>

                  <div className="length-dist">
                    <h5>Length Distribution</h5>
                    <div className="dist-bars">
                      {Object.entries(wordlistStats.length_distribution)
                        .sort(([a], [b]) => Number(a) - Number(b))
                        .map(([length, count]) => (
                          <div key={length} className="bar-item">
                            <span className="length-label">{length}L</span>
                            <div className="bar-container">
                              <div
                                className="bar"
                                style={{
                                  width: `${(count / Math.max(...Object.values(wordlistStats.length_distribution))) * 100}%`
                                }}
                              />
                            </div>
                            <span className="count-label">{count}</span>
                          </div>
                        ))}
                    </div>
                  </div>

                  <div className="letter-freq">
                    <h5>Most Common Letters</h5>
                    <div className="freq-list">
                      {Object.entries(wordlistStats.letter_frequency)
                        .slice(0, 10)
                        .map(([letter, count]) => (
                          <div key={letter} className="freq-item">
                            <span className="letter">{letter}</span>
                            <span className="freq-count">{count}</span>
                          </div>
                        ))}
                    </div>
                  </div>
                </div>
              )}

              <div className="word-grid">
                <h4>Words ({wordlistContent.words.length})</h4>
                <div className="words">
                  {wordlistContent.words.map((word, idx) => (
                    <span key={idx} className="word">
                      {word}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <div className="empty-state">
              <p>Select a wordlist to view its contents</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default WordListPanel;