
BB_DEVICE_NONE            = 0
BB_DEVICE_BB60A           = 1
BB_DEVICE_BB60C           = 2
BB_DEVICE_BB124A          = 3

# Frequencies in Hz
# RT = Real-Time
# TG = Time-Gate
BB_MAX_DEVICES            = 8
BB_SAMPLERATE             = 80000000

# BB60A/C
BB60_MIN_FREQ             = 9.0e3
BB60_MAX_FREQ             = 6.4e9
BB60_MAX_SPAN             = ( BB60_MAX_FREQ - BB60_MIN_FREQ)

# BB124A
BB124_MIN_FREQ            = 9.0e3
BB124_MAX_FREQ            = 12.4e9
BB124_MAX_SPAN            = ( BB124_MAX_FREQ - BB124_MIN_FREQ)

BB_MIN_SPAN               = 20.0
BB_MIN_BW                 = 0.602006912
BB_MAX_BW                 = 10100000
BB_MAX_SWEEP_TIME         = 0.1         # 100ms
BB_MIN_RT_RBW             = 2465.0
BB_MAX_RT_RBW             = 631250.0
BB_MIN_RT_SPAN            = 200.0e3
BB60A_MAX_RT_SPAN         = 20.0e6
BB60C_MAX_RT_SPAN         = 27.0e6
BB_MIN_TG_SPAN            = 200.0e3
BB_MAX_TG_SPAN            = 20.0e6
BB_MIN_SWEEP_TIME         = 0.00001     # 10us in zero-span
BB_RAW_PACKET_SIZE        = 299008
BB_MIN_USB_VOLTAGE        = 4.4
BB_MIN_IQ_BW              = 50.0e3 # 50 kHz min bandwidth

BB_AUTO_ATTEN             = -1.0
BB_MAX_REFERENCE          = 20.0        # dBM
BB_MAX_ATTENUATION        = 30.0        # dB


BB_MIN_DECIMATION         = 0  # 2^0 = 1
BB_MAX_DECIMATION         = 128  # 2^7 = 128


# Gain can be between -1 and MAX
BB_AUTO_GAIN              = -1
BB60_MAX_GAIN             = 3
BB124_MAX_GAIN            = 4
BB60C_MAX_GAIN            = 3

BB_IDLE                   = -1
BB_SWEEPING               = 0x0
BB_REAL_TIME              = 0x1
BB_ZERO_SPAN              = 0x2
BB_TIME_GATE              = 0x3
BB_STREAMING              = 0x4
BB_RAW_PIPE               = BB_STREAMING  # use BB_STREAMING
BB_RAW_SWEEP              = 0x5
BB_RAW_SWEEP_LOOP         = 0x6
BB_AUDIO_DEMOD            = 0x7

BB_NO_SPUR_REJECT         = 0x0
BB_SPUR_REJECT            = 0x1
BB_BYPASS_RF              = 0x2

BB_LOG_SCALE              = 0x0
BB_LIN_SCALE              = 0x1
BB_LOG_FULL_SCALE         = 0x2
BB_LIN_FULL_SCALE         = 0x3

BB_NATIVE_RBW             = 0x0
BB_NON_NATIVE_RBW         = 0x1
BB_6DB_RBW                = 0x2 # n/a

BB_MIN_AND_MAX            = 0x0
BB_AVERAGE                = 0x1
BB_QUASI_PEAK             = 0x4 # n/a

BB_LOG                    = 0x0
BB_VOLTAGE                = 0x1
BB_POWER                  = 0x2
BB_SAMPLE                 = 0x3

BB_NUTALL                 = 0x0
BB_BLACKMAN               = 0x1
BB_HAMMING                = 0x2
BB_FLAT_TOP               = 0x3
BB_FLAT_TOP_EMC_9KHZ      = 0x4
BB_FLAT_TOP_EMC_120KHZ    = 0x5

BB_DEMOD_AM               = 0x0
BB_DEMOD_FM               = 0x1
BB_DEMOD_USB              = 0x2
BB_DEMOD_LSB              = 0x3
BB_DEMOD_CW               = 0x4

# Streaming flags
BB_STREAM_IQ              = 0x0
BB_STREAM_IF              = 0x1
BB_DIRECT_RF              = 0x2   # BB60C only
BB_TIME_STAMP             = 0x10

BB_NO_TRIGGER             = 0x0
BB_VIDEO_TRIGGER          = 0x1
BB_EXTERNAL_TRIGGER       = 0x2

BB_TRIGGER_RISING         = 0x0
BB_TRIGGER_FALLING        = 0x1

BB_TWENTY_MHZ             = 0x0

BB_ENABLE                 = 0x0
BB_DISABLE                = 0x1

BB_PORT1_AC_COUPLED       = 0x00
BB_PORT1_DC_COUPLED       = 0x04
BB_PORT1_INT_REF_OUT      = 0x00
BB_PORT1_EXT_REF_IN       = 0x08
BB_PORT1_OUT_AC_LOAD      = 0x10
BB_PORT1_OUT_LOGIC_LOW    = 0x14
BB_PORT1_OUT_LOGIC_HIGH   = 0x1C

BB_PORT2_OUT_LOGIC_LOW             = 0x00
BB_PORT2_OUT_LOGIC_HIGH            = 0x20
BB_PORT2_IN_TRIGGER_RISING_EDGE    = 0x40
BB_PORT2_IN_TRIGGER_FALLING_EDGE   = 0x60

# Turn off pylint warnings aout these constants not being ALL_UPPERCASE
# I'm aware they *should* be, but I want to conform to the API docs
# pylint: disable=C0103

# Status Codes
# Errors are negative and suffixed with 'Err'
# Errors stop the flow of execution, warnings do not
# Configuration Errors
bbInvalidModeErr             = -112
bbReferenceLevelErr          = -111
bbInvalidVideoUnitsErr       = -110
bbInvalidWindowErr           = -109
bbInvalidBandwidthTypeErr    = -108
bbInvalidSweepTimeErr        = -107
bbBandwidthErr               = -106
bbInvalidGainErr             = -105
bbAttenuationErr             = -104
bbFrequencyRangeErr          = -103
bbInvalidSpanErr             = -102
bbInvalidScaleErr            = -101
bbInvalidDetectorErr         = -100

# General Errors
bbUSBTimeoutErr              = -15
bbDeviceConnectionErr        = -14
bbPacketFramingErr           = -13
bbGPSErr                     = -12
bbGainNotSetErr              = -11
bbDeviceNotIdleErr           = -10
bbDeviceInvalidErr           = -9
bbBufferTooSmallErr          = -8
bbNullPtrErr                 = -7
bbAllocationLimitErr         = -6
bbDeviceAlreadyStreamingErr  = -5
bbInvalidParameterErr        = -4
bbDeviceNotConfiguredErr     = -3
bbDeviceNotStreamingErr      = -2
bbDeviceNotOpenErr           = -1

# No Error
bbNoError                    = 0

# Warnings/Messages
bbAdjustedParameter          = 1
bbADCOverflow                = 2
bbNoTriggerFound             = 3
bbClampedToUpperLimit        = 4
bbClampedToLowerLimit        = 5
bbUncalibratedDevice         = 6

'''

BB_API bbStatus bbOpenDevice(int *device);
BB_API bbStatus bbCloseDevice(int device);

BB_API bbStatus bbConfigureAcquisition(int device, unsigned int detector, unsigned int scale);
BB_API bbStatus bbConfigureCenterSpan(int device, double center, double span);
BB_API bbStatus bbConfigureLevel(int device, double ref, double atten);
BB_API bbStatus bbConfigureGain(int device, int gain);
BB_API bbStatus bbConfigureSweepCoupling(int device, double rbw, double vbw, double sweepTime, unsigned int rbwType, unsigned int rejection);
BB_API bbStatus bbConfigureWindow(int device, unsigned int window);
BB_API bbStatus bbConfigureProcUnits(int device, unsigned int units);
BB_API bbStatus bbConfigureTrigger(int device, unsigned int type, unsigned int edge, double level, double timeout);
BB_API bbStatus bbConfigureTimeGate(int device, double delay, double length, double timeout);
BB_API bbStatus bbConfigureRawSweep(int device, int start, int ppf, int steps, int stepsize);
BB_API bbStatus bbConfigureIO(int device, unsigned int port1, unsigned int port2);
BB_API bbStatus bbConfigureDemod(int device, int modulationType, double freq, float IFBW, float audioLowPassFreq, float audioHighPassFreq, float FMDeemphasis);

BB_API bbStatus bbInitiate(int device, unsigned int mode, unsigned int flag);

BB_API bbStatus bbFetchTrace(int device, int arraySize, double *min, double *max);
BB_API bbStatus bbFetchAudio(int device, float *audio);
BB_API bbStatus bbFetchRawCorrections(int device, float *corrections, int *index, double *startFreq);
BB_API bbStatus bbFetchRaw(int device, float *buffer, int *triggers);
BB_API bbStatus bbFetchRaw_s(int device, short *buffer, int *triggers);
BB_API bbStatus bbFetchRawSweep(int device, short *buffer);
BB_API bbStatus bbStartRawSweepLoop(int device, void(*sweep_callback)(short *buffer, int len));

BB_API bbStatus bbQueryTraceInfo(int device, unsigned int *traceLen, double *binSize, double *start);
BB_API bbStatus bbQueryStreamingCenter(int device, double *center);
BB_API bbStatus bbQueryTimestamp(int device, unsigned int *seconds, unsigned int *nanoseconds);
BB_API bbStatus bbQueryDiagnostics(int device, float *temperature, float *voltage1_8, float *voltage1_2, float *voltageUSB, float *currentUSB);

BB_API bbStatus bbAbort(int device);
BB_API bbStatus bbPreset(int device);
BB_API bbStatus bbSelfCal(int device);
BB_API bbStatus bbSyncCPUtoGPS(int comPort, int baudRate);

BB_API bbStatus bbGetDeviceType(int device, int *type);
BB_API bbStatus bbGetSerialNumber(int device, unsigned int *sid);
BB_API bbStatus bbGetFirmwareVersion(int device, int *version);

BB_API const char* bbGetAPIVersion();
BB_API const char* bbGetErrorString(bbStatus status);

'''
