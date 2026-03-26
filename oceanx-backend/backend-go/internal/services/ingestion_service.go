package services

import (
	"fmt"
	"io"
	"mime/multipart"
	"os"
	"path/filepath"
	"strings"
	"time"

	"github.com/google/uuid"
)

type SavedTelemetryFile struct {
	OriginalFilename string `json:"original_filename"`
	StoredFilename   string `json:"stored_filename"`
	StoredPath       string `json:"stored_path"`
	SizeBytes        int64  `json:"size_bytes"`
}

type RejectedTelemetryFile struct {
	Filename string `json:"filename"`
	Reason   string `json:"reason"`
}

type IngestionResult struct {
	BatchID      string                  `json:"batch_id"`
	BatchDir     string                  `json:"batch_dir"`
	SavedCount   int                     `json:"saved_count"`
	RejectedCount int                    `json:"rejected_count"`
	Saved        []SavedTelemetryFile    `json:"saved"`
	Rejected     []RejectedTelemetryFile `json:"rejected"`
}

type IngestionService struct {
	StorageDir string
}

func NewIngestionService(storageDir string) *IngestionService {
	return &IngestionService{StorageDir: storageDir}
}

func (s *IngestionService) SaveTelemetryFiles(files []*multipart.FileHeader) (*IngestionResult, error) {
	if len(files) == 0 {
		return nil, fmt.Errorf("no files uploaded")
	}

	if err := os.MkdirAll(s.StorageDir, 0o755); err != nil {
		return nil, err
	}

	batchID := fmt.Sprintf("%s_%s", time.Now().UTC().Format("20060102T150405Z"), uuid.NewString())
	batchDir := filepath.Join(s.StorageDir, batchID)
	if err := os.MkdirAll(batchDir, 0o755); err != nil {
		return nil, err
	}

	result := &IngestionResult{
		BatchID:  batchID,
		BatchDir: batchDir,
		Saved:    make([]SavedTelemetryFile, 0),
		Rejected: make([]RejectedTelemetryFile, 0),
	}

	for _, fileHeader := range files {
		originalName := fileHeader.Filename
		ext := strings.ToLower(filepath.Ext(originalName))
		if ext != ".json" && ext != ".txt" {
			result.Rejected = append(result.Rejected, RejectedTelemetryFile{
				Filename: originalName,
				Reason:   "unsupported file type (only .json and .txt allowed)",
			})
			continue
		}

		safeName := filepath.Base(originalName)
		if safeName == "." || safeName == string(filepath.Separator) || safeName == "" {
			result.Rejected = append(result.Rejected, RejectedTelemetryFile{
				Filename: originalName,
				Reason:   "invalid filename",
			})
			continue
		}

		storedName := uniqueFilename(batchDir, safeName)
		dstPath := filepath.Join(batchDir, storedName)

		src, err := fileHeader.Open()
		if err != nil {
			result.Rejected = append(result.Rejected, RejectedTelemetryFile{
				Filename: originalName,
				Reason:   fmt.Sprintf("failed to open upload: %v", err),
			})
			continue
		}

		dst, err := os.Create(dstPath)
		if err != nil {
			src.Close()
			result.Rejected = append(result.Rejected, RejectedTelemetryFile{
				Filename: originalName,
				Reason:   fmt.Sprintf("failed to create destination: %v", err),
			})
			continue
		}

		written, copyErr := io.Copy(dst, src)
		srcCloseErr := src.Close()
		dstCloseErr := dst.Close()
		if copyErr != nil || srcCloseErr != nil || dstCloseErr != nil {
			_ = os.Remove(dstPath)
			reason := copyErr
			if reason == nil {
				reason = srcCloseErr
			}
			if reason == nil {
				reason = dstCloseErr
			}
			result.Rejected = append(result.Rejected, RejectedTelemetryFile{
				Filename: originalName,
				Reason:   fmt.Sprintf("failed to save file: %v", reason),
			})
			continue
		}

		result.Saved = append(result.Saved, SavedTelemetryFile{
			OriginalFilename: originalName,
			StoredFilename:   storedName,
			StoredPath:       dstPath,
			SizeBytes:        written,
		})
	}

	result.SavedCount = len(result.Saved)
	result.RejectedCount = len(result.Rejected)

	return result, nil
}

func uniqueFilename(dir string, filename string) string {
	if _, err := os.Stat(filepath.Join(dir, filename)); os.IsNotExist(err) {
		return filename
	}

	ext := filepath.Ext(filename)
	base := strings.TrimSuffix(filename, ext)
	for i := 1; ; i++ {
		candidate := fmt.Sprintf("%s_%d%s", base, i, ext)
		if _, err := os.Stat(filepath.Join(dir, candidate)); os.IsNotExist(err) {
			return candidate
		}
	}
}