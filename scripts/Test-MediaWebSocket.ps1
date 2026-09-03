param(
    [string]$Uri = 'ws://localhost:8080/media',

    [Parameter(Mandatory = $true)]
    [string]$WavPath,

    [ValidateRange(0, 10000)]
    [int]$StartDelayMilliseconds = 500,

    [ValidateRange(0, 30000)]
    [int]$FinalWaitMilliseconds = 1500,

    [switch]$Realtime
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# Gemini/Exotel media target:
# 16,000 Hz, 16-bit, mono PCM
$TargetSampleRate = 16000
$TargetBitsPerSample = 16
$TargetChannels = 1

# Exactly 100 ms:
# 16,000 samples/sec * 0.1 sec * 2 bytes/sample = 3,200 bytes
$ChunkMilliseconds = 100
$BytesPerSample = 2
$TargetChunkBytes = 3200

if (-not (Test-Path -LiteralPath $WavPath -PathType Leaf)) {
    throw "WAV file not found: $WavPath"
}

$extension = [System.IO.Path]::GetExtension($WavPath)
if ($extension -ne '.wav') {
    throw "Input file must be a .wav file."
}

function Read-UInt16LE {
    param(
        [byte[]]$Bytes,
        [int]$Offset
    )

    return [BitConverter]::ToUInt16($Bytes, $Offset)
}

function Read-UInt32LE {
    param(
        [byte[]]$Bytes,
        [int]$Offset
    )

    return [BitConverter]::ToUInt32($Bytes, $Offset)
}

function Convert-PcmToTarget {
    param(
        [byte[]]$InputPcm,
        [int]$InputSampleRate,
        [int]$InputChannels,
        [int]$InputBitsPerSample
    )

    if ($InputBitsPerSample -ne 16) {
        throw "Only 16-bit PCM WAV files are supported. Found $InputBitsPerSample-bit audio."
    }

    if ($InputChannels -lt 1) {
        throw "Invalid WAV channel count."
    }

    $inputSampleCount = [int]($InputPcm.Length / 2 / $InputChannels)

    if ($inputSampleCount -le 0) {
        throw "WAV file contains no PCM samples."
    }

    # Read interleaved 16-bit samples.
    $samples = [int[]]::new($inputSampleCount * $InputChannels)

    for ($i = 0; $i -lt $samples.Length; $i++) {
        $offset = $i * 2

        $low = $InputPcm[$offset]
        $high = $InputPcm[$offset + 1]

        # Cast before shifting: PowerShell preserves the [byte] type for a byte
        # shift, which would otherwise discard every high byte of the PCM16 sample.
        $value = [int]([uint16]([int]$low -bor ([int]$high -shl 8)))

        if ($value -ge 32768) {
            $value -= 65536
        }

        $samples[$i] = $value
    }

    # Downmix to mono if necessary.
    $mono = [int[]]::new($inputSampleCount)

    for ($i = 0; $i -lt $inputSampleCount; $i++) {
        if ($InputChannels -eq 1) {
            $mono[$i] = $samples[$i]
        }
        else {
            $sum = 0L

            for ($channel = 0; $channel -lt $InputChannels; $channel++) {
                $sum += $samples[($i * $InputChannels) + $channel]
            }

            $mono[$i] = [int]($sum / $InputChannels)
        }
    }

    # Resample to 16 kHz using linear interpolation.
    if ($InputSampleRate -eq $TargetSampleRate) {
        $outputSamples = $mono
    }
    else {
        $outputSampleCount = [int][Math]::Round(
            $inputSampleCount * $TargetSampleRate / [double]$InputSampleRate
        )

        $outputSamples = [int[]]::new($outputSampleCount)

        for ($i = 0; $i -lt $outputSampleCount; $i++) {
            $sourcePosition =
                $i * ($InputSampleRate / [double]$TargetSampleRate)

            $leftIndex = [int][Math]::Floor($sourcePosition)
            $fraction = $sourcePosition - $leftIndex

            if ($leftIndex -ge ($inputSampleCount - 1)) {
                $outputSamples[$i] = $mono[$inputSampleCount - 1]
                continue
            }

            $left = $mono[$leftIndex]
            $right = $mono[$leftIndex + 1]

            $interpolated =
                $left + (($right - $left) * $fraction)

            $outputSamples[$i] = [int][Math]::Round($interpolated)
        }
    }

    # Convert samples back to little-endian PCM16.
    $outputBytes = [byte[]]::new($outputSamples.Length * 2)

    for ($i = 0; $i -lt $outputSamples.Length; $i++) {
        $value = $outputSamples[$i]

        if ($value -gt 32767) {
            $value = 32767
        }

        if ($value -lt -32768) {
            $value = -32768
        }

        $unsigned = [uint16]($value -band 0xFFFF)

        $outputBytes[$i * 2] = [byte]($unsigned -band 0xFF)
        $outputBytes[($i * 2) + 1] = [byte](($unsigned -shr 8) -band 0xFF)
    }

    return $outputBytes
}

function Read-WavPcm {
    param(
        [string]$Path
    )

    $bytes = [System.IO.File]::ReadAllBytes($Path)

    if ($bytes.Length -lt 44) {
        throw "WAV file is too small."
    }

    $riff = [System.Text.Encoding]::ASCII.GetString($bytes, 0, 4)
    $wave = [System.Text.Encoding]::ASCII.GetString($bytes, 8, 4)

    if ($riff -ne 'RIFF' -or $wave -ne 'WAVE') {
        throw "File is not a standard RIFF/WAVE file."
    }

    $position = 12

    $audioFormat = $null
    $channels = $null
    $sampleRate = $null
    $bitsPerSample = $null
    $dataBytes = $null

    while (($position + 8) -le $bytes.Length) {

        $chunkId =
            [System.Text.Encoding]::ASCII.GetString(
                $bytes,
                $position,
                4
            )

        $chunkSize = [int](Read-UInt32LE $bytes ($position + 4))

        $chunkDataStart = $position + 8

        if (($chunkDataStart + $chunkSize) -gt $bytes.Length) {
            throw "Invalid WAV chunk size."
        }

        switch ($chunkId) {

            'fmt ' {
                if ($chunkSize -lt 16) {
                    throw "Invalid WAV fmt chunk."
                }

                $audioFormat =
                    Read-UInt16LE $bytes $chunkDataStart

                $channels =
                    Read-UInt16LE $bytes ($chunkDataStart + 2)

                $sampleRate =
                    [int](Read-UInt32LE $bytes ($chunkDataStart + 4))

                $bitsPerSample =
                    Read-UInt16LE $bytes ($chunkDataStart + 14)
            }

            'data' {
                $dataBytes = [byte[]]::new($chunkSize)

                [Array]::Copy(
                    $bytes,
                    $chunkDataStart,
                    $dataBytes,
                    0,
                    $chunkSize
                )

                break
            }
        }

        # WAV chunks are word aligned.
        $position += 8 + $chunkSize

        if (($position % 2) -ne 0) {
            $position++
        }
    }

    if ($null -eq $audioFormat) {
        throw "WAV fmt chunk not found."
    }

    if ($audioFormat -ne 1) {
        throw "Only uncompressed PCM WAV files are supported. Audio format=$audioFormat."
    }

    if ($null -eq $dataBytes) {
        throw "WAV data chunk not found."
    }

    Write-Host "WAV input:"
    Write-Host "  Sample rate : $sampleRate Hz"
    Write-Host "  Channels    : $channels"
    Write-Host "  Bit depth   : $bitsPerSample"
    Write-Host "  PCM bytes   : $($dataBytes.Length)"

    $normalizedPcm = Convert-PcmToTarget `
        -InputPcm $dataBytes `
        -InputSampleRate $sampleRate `
        -InputChannels $channels `
        -InputBitsPerSample $bitsPerSample

    # Prevent PowerShell from unrolling the byte[] into pipeline elements.
    return ,([byte[]]$normalizedPcm)
}

# Guard the helper's signed PCM16 decoding before any audio is transmitted.
$conversionProbe = Convert-PcmToTarget `
    -InputPcm ([byte[]](0x00, 0x80, 0xFF, 0x7F)) `
    -InputSampleRate $TargetSampleRate `
    -InputChannels 1 `
    -InputBitsPerSample 16

if ([Convert]::ToHexString($conversionProbe) -ne '0080FF7F') {
    throw 'Internal PCM16 conversion validation failed.'
}

function Send-JsonMessage {
    param(
        [Parameter(Mandatory = $true)]
        [hashtable]$Message
    )

    $json = $Message | ConvertTo-Json -Compress -Depth 12

    $bytes = [System.Text.Encoding]::UTF8.GetBytes($json)

    $segment = [System.ArraySegment[byte]]::new($bytes)

    $client.SendAsync(
        $segment,
        [System.Net.WebSockets.WebSocketMessageType]::Text,
        $true,
        $cancellationToken
    ).GetAwaiter().GetResult() | Out-Null
}

# ------------------------------------------------------------
# Load and normalize WAV
# ------------------------------------------------------------

[byte[]]$pcm = Read-WavPcm -Path $WavPath
if ($pcm.GetType() -ne [byte[]]) { throw "Normalized PCM must be byte[]. Actual type: $($pcm.GetType().FullName)" }

Write-Output ""
Write-Output "Normalized audio:"
Write-Output "  Sample rate : 16000 Hz"
Write-Output "  Channels    : 1"
Write-Output "  Bit depth   : 16-bit PCM"
Write-Output "  Chunk size  : 3200 bytes"
Write-Output "  Chunk time  : 100 ms"

$totalChunks = [int][Math]::Ceiling(
    $pcm.Length / [double]$TargetChunkBytes
)

$durationSeconds =
    $pcm.Length / 2.0 / $TargetSampleRate

Write-Output "  Duration    : $([Math]::Round($durationSeconds, 2)) seconds"
Write-Output "  Chunks      : $totalChunks"

# ------------------------------------------------------------
# WebSocket
# ------------------------------------------------------------

$client = [System.Net.WebSockets.ClientWebSocket]::new()
$cancellationToken = [System.Threading.CancellationToken]::None
$callSid = 'CA-local-wav-test'
$streamSid = 'MZ-local-wav-test-stream'

try {

    Write-Output ""
    Write-Output "Connecting to $Uri ..."

    $client.ConnectAsync(
        [Uri]$Uri,
        $cancellationToken
    ).GetAwaiter().GetResult() | Out-Null

    Write-Output "Connected."

    # Exotel-style connected event
    Send-JsonMessage @{
        event = 'connected'
    }

    # Exotel-style start event
    Send-JsonMessage @{
        event = 'start'
        sequence_number = 1
        stream_sid = $streamSid

        start = @{
            stream_sid = $streamSid
            call_sid = $callSid
            account_sid = 'AC-local-wav-test'

            from = '+910000000001'
            to = '+910000000002'

            custom_parameters = @{}

            media_format = @{
                encoding = 'audio/x-raw'
                sample_rate = '16000'
                bit_rate = '16'
            }
        }
    }

    if ($StartDelayMilliseconds -gt 0) {
        Write-Output "Waiting $StartDelayMilliseconds ms for STT setup..."

        Start-Sleep -Milliseconds $StartDelayMilliseconds
    }

    Write-Output ""
    Write-Output "Streaming audio..."

    $sequenceNumber = 2
    $sentBytes = 0

    for ($chunkIndex = 0; $chunkIndex -lt $totalChunks; $chunkIndex++) {

        $offset = $chunkIndex * $TargetChunkBytes

        $remaining = $pcm.Length - $offset

        $bytesThisChunk =
            [Math]::Min($TargetChunkBytes, $remaining)

        # Always send exactly 3200 bytes.
        $chunk = [byte[]]::new($TargetChunkBytes)

        if ($bytesThisChunk -gt 0) {
            [Array]::Copy(
                $pcm,
                $offset,
                $chunk,
                0,
                $bytesThisChunk
            )
        }

        $timestamp =
            $chunkIndex * $ChunkMilliseconds

        Send-JsonMessage @{
            event = 'media'
            sequence_number = $sequenceNumber
            stream_sid = $streamSid

            media = @{
                chunk = $chunkIndex + 1
                timestamp = $timestamp
                payload = [Convert]::ToBase64String($chunk)
            }
        }

        $sequenceNumber++
        $sentBytes += $bytesThisChunk

        if (
            (($chunkIndex + 1) % 10 -eq 0) -or
            ($chunkIndex -eq $totalChunks - 1)
        ) {
            $percent =
                [Math]::Round(
                    (($chunkIndex + 1) / [double]$totalChunks) * 100,
                    1
                )

            Write-Output `
                "  Sent chunk $($chunkIndex + 1)/$totalChunks ($percent%)"
        }

        if (
            $Realtime -and
            ($chunkIndex -lt $totalChunks - 1)
        ) {
            Start-Sleep -Milliseconds $ChunkMilliseconds
        }
    }

    Write-Output ""
    Write-Output "Audio streaming complete."
    Write-Output "  Original PCM bytes sent: $sentBytes"
    Write-Output "  100-ms chunks sent      : $totalChunks"

    # Give Gemini a little time to emit final transcription.
    Write-Output "Waiting for final transcription..."

    Start-Sleep -Milliseconds $FinalWaitMilliseconds

    # Exotel-style stop event
    Send-JsonMessage @{
        event = 'stop'
        sequence_number = $sequenceNumber
        stream_sid = $streamSid

        stop = @{
            call_sid = $callSid
            account_sid = 'AC-local-wav-test'
            reason = 'completed'
        }
    }

    Write-Output ""
    Write-Output "Sent connected/start/$totalChunks media frame(s)/stop successfully."

}
finally {

    if ($null -ne $client) {
        $client.Dispose()
    }
}
