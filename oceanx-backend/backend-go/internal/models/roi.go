package models

type Roi struct {
	ID       string
	FrameID  string
	FrameIdx int
	VideoID  string
	X1       int
	Y1       int
	X2       int
	Y2       int
}
