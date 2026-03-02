'use client';

import { useEffect, useState } from 'react';
import { Video } from '@/types';

interface VideoListProps {
  onSelectVideo: (videoId: string) => void;
}

export function VideoList({ onSelectVideo }: VideoListProps) {
  const [videos, setVideos] = useState<Video[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string>('');

  useEffect(() => {
    const fetchVideos = async () => {
      try {
        setLoading(true);
        const response = await fetch('/videos');
        if (!response.ok) {
          throw new Error(`Failed to fetch videos: ${response.statusText}`);
        }
        const data = await response.json();
        setVideos(data);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch videos');
        console.error('Error fetching videos:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchVideos();
  }, []);

  const handleSelect = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const videoId = e.target.value;
    setSelectedId(videoId);
    if (videoId) {
      onSelectVideo(videoId);
    }
  };

  if (loading) {
    return <div className="text-gray-600">Loading videos...</div>;
  }

  if (error) {
    return <div className="text-red-600">Error: {error}</div>;
  }

  if (videos.length === 0) {
    return <div className="text-gray-600">No videos found. Upload a video to get started.</div>;
  }

  return (
    <div className="space-y-2">
      <label htmlFor="video-select" className="block text-sm font-medium text-gray-700">
        Select Video
      </label>
      <select
        id="video-select"
        value={selectedId}
        onChange={handleSelect}
        className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
      >
        <option value="">-- Select a video --</option>
        {videos.map((video) => (
          <option key={video.id} value={video.id}>
            {video.filename} ({video.status}) - {new Date(video.created_at).toLocaleString()}
          </option>
        ))}
      </select>
    </div>
  );
}
