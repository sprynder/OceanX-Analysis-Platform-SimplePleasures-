import { useVideoProgress } from '@/hooks/useVideoProgress';

interface ProcessingProgressProps {
  videoId: string | null;
  isProcessing: boolean;
}

export function ProcessingProgress({
  videoId,
  isProcessing,
}: ProcessingProgressProps) {
  const { isConnected, lastEvent } = useVideoProgress(videoId);

  if (!isProcessing || !lastEvent) return null;

  const { frames_processed, rois_detected, message, type, total_frames } = lastEvent;

  // Calculate progress percentage
  const progressPercent = total_frames && frames_processed 
    ? Math.round((frames_processed / total_frames) * 100)
    : 0;

  return (
    <div className="mt-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-semibold text-blue-900">
          {type === 'processing_complete'
            ? '✓ Processing Complete'
            : '⏳ Processing Video'}
        </h3>
        <div className="flex items-center gap-2">
          <div
            className={`w-2 h-2 rounded-full ${
              isConnected ? 'bg-green-500' : 'bg-yellow-500'
            }`}
          />
          <span className="text-xs text-gray-600">
            {isConnected ? 'Live' : 'Buffering...'}
          </span>
        </div>
      </div>

      {message && (
        <p className="text-sm text-blue-800 mb-3">{message}</p>
      )}

      <div className="space-y-3">
        {frames_processed !== undefined && (
          <div>
            <div className="flex justify-between text-xs text-gray-700 mb-1">
              <span className="font-medium">Frame Progress</span>
              <span className="font-semibold text-blue-700">
                {frames_processed} / {total_frames || '?'} frames
              </span>
            </div>
            <div className="w-full bg-gray-300 rounded-full h-3 overflow-hidden">
              <div
                className="bg-gradient-to-r from-blue-500 to-blue-600 h-3 rounded-full transition-all duration-500 ease-out"
                style={{
                  width: `${Math.max(progressPercent, 2)}%`,
                }}
              />
            </div>
            <div className="text-right mt-1">
              <span className="text-xs text-gray-600">{progressPercent}%</span>
            </div>
          </div>
        )}

        {rois_detected !== undefined && (
          <div className="bg-white rounded p-3 border border-blue-100">
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-700">ROIs Detected</span>
              <span className="text-xl font-bold text-blue-600">{rois_detected}</span>
            </div>
          </div>
        )}
      </div>

      {type === 'processing_complete' && (
        <div className="mt-3 p-2 bg-green-100 rounded border border-green-300 text-sm text-green-700 font-medium text-center">
          ✓ Ready to view results
        </div>
      )}
    </div>
  );
}
