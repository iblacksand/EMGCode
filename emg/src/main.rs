use clap::Parser;
use rustfft::{FftPlanner, num_complex::Complex};
use std::cmp::Ordering;
use std::fs::File;
use std::io::{BufRead, BufReader};

#[derive(Parser)]
struct Args {
    /// Input file containing: time value
    input: String,
}

fn hann_window(n: usize) -> Vec<f64> {
    (0..n)
        .map(|i| 0.5 * (1.0 - (2.0 * std::f64::consts::PI * i as f64 / (n as f64 - 1.0)).cos()))
        .collect()
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args = Args::parse();

    let file = File::open(args.input)?;
    let reader = BufReader::new(file);

    let mut times = Vec::<f64>::new();
    let mut values = Vec::<f64>::new();

    for line in reader.lines() {
        let line = line?;

        if line.trim().is_empty() {
            continue;
        }

        let fields: Vec<&str> = line.split_whitespace().collect();

        if fields.len() < 2 {
            continue;
        }

        let t: f64 = match fields[0].parse() {
            Ok(v) => v,
            Err(_) => continue,
        };

        let v: f64 = match fields[1].parse() {
            Ok(v) => v,
            Err(_) => continue,
        };

        times.push(t);
        values.push(v);
    }

    let n = values.len();

    if n < 2 {
        return Err("Need at least two samples".into());
    }

    // Estimate sample rate
    let duration = times[n - 1] - times[0];

    if duration <= 0.0 {
        return Err("Invalid timestamps".into());
    }

    let sample_rate = (n as f64 - 1.0) / duration;

    println!("Samples: {}", n);
    println!("Duration: {:.3} sec", duration);
    println!("Sampling rate: {:.2} Hz", sample_rate);

    // Remove DC offset
    let mean = values.iter().sum::<f64>() / n as f64;

    // Apply Hann window
    let window = hann_window(n);

    let mut buffer: Vec<Complex<f64>> = values
        .iter()
        .zip(window.iter())
        .map(|(x, w)| Complex {
            re: (x - mean) * w,
            im: 0.0,
        })
        .collect();

    // FFT
    let mut planner = FftPlanner::<f64>::new();
    let fft = planner.plan_fft_forward(n);

    fft.process(&mut buffer);

    let nyquist_bin = n / 2;

    // Hann coherent gain correction
    let coherent_gain = 0.5;

    let mut spectrum = Vec::<(f64, f64)>::new();

    for i in 1..nyquist_bin {
        let freq = i as f64 * sample_rate / n as f64;

        let magnitude = (buffer[i].norm() / n as f64) / coherent_gain;

        let power = magnitude * magnitude;

        spectrum.push((freq, power));
    }

    // EMG frequency bands
    let bands = vec![
        (20.0, 50.0),
        (50.0, 100.0),
        (100.0, 150.0),
        (150.0, 250.0),
        (250.0, 350.0),
        (350.0, 450.0),
    ];

    let mut band_powers = Vec::<(String, f64)>::new();

    for (low, high) in bands {
        let mut power = 0.0;

        for (freq, p) in &spectrum {
            if *freq >= low && *freq < high {
                power += *p;
            }
        }

        band_powers.push((format!("{:.0}-{:.0} Hz", low, high), power));
    }

    let total_power: f64 = spectrum.iter().map(|(_, p)| p).sum();

    band_powers.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(Ordering::Equal));

    println!("\nBand Power Ranking");
    println!("==================");

    for (rank, (band, power)) in band_powers.iter().enumerate() {
        println!(
            "#{:<2} {:<12} {:>12.6} ({:>6.2}%)",
            rank + 1,
            band,
            power,
            100.0 * power / total_power
        );
    }

    // Mean Frequency (MNF)
    let weighted_freq_sum: f64 = spectrum.iter().map(|(f, p)| f * p).sum();

    let mean_frequency = weighted_freq_sum / total_power;

    // Median Frequency (MDF)
    let mut cumulative_power = 0.0;
    let half_power = total_power / 2.0;

    let mut median_frequency = 0.0;

    for (freq, power) in &spectrum {
        cumulative_power += power;

        if cumulative_power >= half_power {
            median_frequency = *freq;
            break;
        }
    }

    println!("\nEMG Metrics");
    println!("===========");
    println!("Mean Frequency (MNF):   {:.2} Hz", mean_frequency);
    println!("Median Frequency (MDF): {:.2} Hz", median_frequency);

    Ok(())
}
