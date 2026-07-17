import type { Metadata } from "next";
import { AboutHeader } from "./AboutHeader";
import { ATTRIBUTION, BRAND, CITY } from "@/lib/city.config";

export const metadata: Metadata = {
  title: `About - ${BRAND}`,
  description: `How ${BRAND} uses satellite data to track the health of ${CITY}'s lakes. Methodology, data sources, and limitations.`,
};

export default function AboutPage() {
  return (
    <main className="min-h-screen bg-background">
      <article className="max-w-3xl mx-auto px-4 py-12">
        {/* Intro */}
        <AboutHeader />
        <p className="text-foreground/80 leading-relaxed mb-4">
          {BRAND} points satellites at {CITY}&apos;s lakes and tracks
          what&apos;s happening to them. Every few days, the European Space
          Agency&apos;s Sentinel-2 satellites photograph the city at 10-meter
          resolution. We turn those pixels into numbers that tell you which
          lakes are thriving and which ones need help.
        </p>
        <p className="text-foreground/80 leading-relaxed mb-4">
          Think of it as a fitness tracker, but for lakes. Except the
          &ldquo;wearable&rdquo; is a satellite orbiting 786 km above your
          head, and instead of counting steps it&apos;s measuring how much
          water is left and whether it&apos;s turning green.
        </p>

        {/* What we measure */}
        <h2 className="text-2xl font-bold text-white mb-4 mt-12">
          What the site measures
        </h2>
        <p className="text-foreground/80 leading-relaxed mb-4">
          Everything here is derived from{" "}
          <strong className="text-white">Copernicus Sentinel-2 L2A</strong>{" "}
          imagery, processed on{" "}
          <strong className="text-white">Google Earth Engine</strong>. The
          satellites revisit the same spot roughly every{" "}
          <strong className="text-white">5 days</strong>, and each pixel
          covers <strong className="text-white">10 meters</strong> on the
          ground. For every tracked lake we compute three core metrics:
        </p>
        <ul className="list-disc list-inside text-foreground/70 space-y-2 mb-4">
          <li>
            <strong className="text-white">Water area</strong> — how much open
            water the lake surface holds right now, and how that changes over
            months and years.
          </li>
          <li>
            <strong className="text-white">Algae fraction</strong> — how much
            of the water surface reads as algae, a proxy for eutrophication.
          </li>
          <li>
            <strong className="text-white">Health score</strong> — a single
            0-100 number combining area stability, algae, water presence, and
            long-term trend.
          </li>
        </ul>
        <p className="text-foreground/80 leading-relaxed mb-4">
          Each lake also gets a <strong className="text-white">timelapse</strong>{" "}
          — an animated strip of satellite frames so you can watch it shrink,
          refill, or bloom over the years with your own eyes.
        </p>

        {/* How it works */}
        <h2 className="text-2xl font-bold text-white mb-4 mt-12">
          How it works
        </h2>

        <h3 className="text-xl font-semibold text-white mb-3 mt-8">
          Water detection (NDWI)
        </h3>
        <p className="text-foreground/80 leading-relaxed mb-4">
          We use the{" "}
          <strong className="text-white">
            Normalized Difference Water Index
          </strong>{" "}
          to figure out where the water is. The formula is simple:
        </p>
        <div className="bg-white/5 border border-white/10 rounded-lg px-6 py-4 my-4">
          <code className="text-lg text-emerald-400 block text-center mb-3">
            NDWI = (B03 - B08) / (B03 + B08)
          </code>
          <p className="text-xs text-foreground/50 text-center">
            B03 = Green band (560nm) | B08 = Near-Infrared band (842nm) | Both at 10m resolution
          </p>
        </div>
        <p className="text-foreground/80 leading-relaxed mb-4">
          Water reflects green light and absorbs near-infrared (NIR), so water
          pixels get a positive NDWI value (closer to +1). Land does the opposite
          (closer to -1). We use{" "}
          <strong className="text-white">Otsu&apos;s method</strong> -- an
          adaptive thresholding technique -- to find the water/not-water
          boundary for each image automatically. Otsu looks at the histogram of
          all NDWI values across the lake and finds the value that best separates
          the two peaks (water and land). If the histogram is weird (fully cloudy,
          no clear pixels), we fall back to a fixed threshold of 0.3.
        </p>
        <p className="text-foreground/80 leading-relaxed mb-4">
          Once we know which pixels are water, we count them and multiply by
          the pixel area (100 m&sup2; each at 10m resolution) to get the total
          water surface area in square meters. That&apos;s the{" "}
          <strong className="text-white">Water Area</strong> number you see on
          each lake&apos;s page.
        </p>

        <h3 className="text-xl font-semibold text-white mb-3 mt-8">
          Cloud masking
        </h3>
        <p className="text-foreground/80 leading-relaxed mb-4">
          Before computing anything, we strip out clouds using the{" "}
          <strong className="text-white">SCL (Scene Classification Layer)</strong>{" "}
          band that comes with every Sentinel-2 image. We only keep pixels
          classified as vegetation, bare soil, or water (SCL values 4, 5, 6).
          Everything else -- clouds, cloud shadows, saturated pixels, snow --
          gets masked out. If more than <strong className="text-white">30% of
          the lake area</strong> is cloudy, we throw out the entire image. No
          point measuring clouds.
        </p>

        <h3 className="text-xl font-semibold text-white mb-3 mt-8">
          Algae detection
        </h3>
        <div className="bg-white/5 border border-white/10 rounded-lg px-6 py-4 my-4">
          <code className="text-lg text-emerald-400 block text-center mb-3">
            NDVI = (B08 - B04) / (B08 + B04)
          </code>
          <p className="text-xs text-foreground/50 text-center">
            B08 = Near-Infrared (842nm) | B04 = Red (665nm) | Only computed on water pixels
          </p>
        </div>
        <p className="text-foreground/80 leading-relaxed mb-4">
          We run NDVI (the vegetation index) on pixels we&apos;ve already
          classified as water. Healthy water has low NDVI. But when algae blooms
          on the surface, it reflects NIR light just like plants on land, pushing
          NDVI up. We flag any water pixel with{" "}
          <strong className="text-white">NDVI &gt; 0.15</strong> as showing algae.
          The <strong className="text-white">Algae Level</strong> percentage you see
          is the fraction of the lake&apos;s water surface where this is happening.
        </p>
        <p className="text-foreground/80 leading-relaxed mb-4">
          High algae = eutrophication, usually from sewage or fertilizer runoff
          feeding the lake nutrients it can&apos;t handle.
        </p>

        <h3 className="text-xl font-semibold text-white mb-3 mt-8">
          Health score (0-100)
        </h3>
        <p className="text-foreground/80 leading-relaxed mb-2">
          Each lake gets a composite health score, weighted like this:
        </p>
        <ul className="list-disc list-inside text-foreground/70 space-y-2 mb-4">
          <li>
            <strong className="text-white">40% Area stability</strong> -- is the
            lake shrinking?
          </li>
          <li>
            <strong className="text-white">30% Algae levels</strong> -- is it
            getting greener?
          </li>
          <li>
            <strong className="text-white">20% Water presence</strong> -- is
            there actually water?
          </li>
          <li>
            <strong className="text-white">10% Trend</strong> -- is it getting
            better or worse over time?
          </li>
        </ul>
        <div className="bg-white/5 border border-white/10 rounded-lg p-4 my-4 space-y-2">
          <div className="flex items-center gap-3">
            <span className="inline-block w-3 h-3 rounded-full bg-green-500" />
            <span className="text-foreground/80"><strong className="text-white">60-100:</strong> Healthy. Stable water area, low algae, positive trend.</span>
          </div>
          <div className="flex items-center gap-3">
            <span className="inline-block w-3 h-3 rounded-full bg-yellow-500" />
            <span className="text-foreground/80"><strong className="text-white">30-60:</strong> Struggling. Some shrinkage or moderate algae. Worth watching.</span>
          </div>
          <div className="flex items-center gap-3">
            <span className="inline-block w-3 h-3 rounded-full bg-red-500" />
            <span className="text-foreground/80"><strong className="text-white">0-30:</strong> Distressed. Shrinking, high algae, declining trend. Needs attention.</span>
          </div>
        </div>
        <p className="text-foreground/80 leading-relaxed mb-4">
          The score needs at least 10 monthly observations to compute (roughly
          a year of data). Lakes with fewer observations show &ldquo;--&rdquo;
          instead of a score. The trend component uses linear regression on the
          water area time series -- so a lake that&apos;s been steadily shrinking
          gets penalized even if it&apos;s still relatively large.
        </p>

        <h3 className="text-xl font-semibold text-white mb-3 mt-8">
          Time intervals &amp; timelapses
        </h3>
        <p className="text-foreground/80 leading-relaxed mb-4">
          We offer three ways to view the data:{" "}
          <strong className="text-white">raw</strong> (every usable satellite
          pass),{" "}
          <strong className="text-white">monthly</strong> (best observation per
          month), and <strong className="text-white">yearly</strong> (annual
          averages). Timelapse frames are rendered from the least cloudy image
          in each period, so the animation stays watchable even through cloudy
          seasons.
        </p>

        {/* Data Pipeline */}
        <h2 className="text-2xl font-bold text-white mb-4 mt-12">
          The data pipeline
        </h2>
        <p className="text-foreground/80 leading-relaxed mb-4">
          Here&apos;s what happens every time we process a lake, step by step:
        </p>
        <ol className="list-decimal list-inside text-foreground/70 space-y-3 mb-4">
          <li>
            <strong className="text-white">Query Google Earth Engine</strong> for
            Sentinel-2 images covering the lake polygon. We pick the{" "}
            <strong className="text-white">least cloudy image per month</strong>.
          </li>
          <li>
            <strong className="text-white">Mask clouds</strong> using the SCL
            band. Reject the image entirely if &gt;30% of the lake is obscured.
          </li>
          <li>
            <strong className="text-white">Compute NDWI</strong> on clear pixels.
            Classify water vs land using Otsu&apos;s threshold.
          </li>
          <li>
            <strong className="text-white">Measure water area</strong> by
            counting water pixels and multiplying by 100 m&sup2; per pixel.
          </li>
          <li>
            <strong className="text-white">Detect algae</strong> by running NDVI
            on water pixels. Flag anything above 0.15.
          </li>
          <li>
            <strong className="text-white">Store the observation</strong> --
            date, water area, mean NDWI, algae fraction, cloud percentage.
          </li>
          <li>
            <strong className="text-white">Compute health score</strong> from
            the full history of observations (needs 10+ months of data).
          </li>
        </ol>
        <p className="text-foreground/80 leading-relaxed mb-4">
          All the heavy computation (steps 1-5) happens on Google&apos;s
          servers via Earth Engine. We only download the final numbers, not the
          raw satellite images. This means we can process a decade of data for
          a lake in about a minute.
        </p>

        {/* Data Sources */}
        <h2 className="text-2xl font-bold text-white mb-4 mt-12">
          Data sources
        </h2>
        <p className="text-foreground/80 leading-relaxed mb-4">
          Copernicus Sentinel-2 L2A data is provided free of charge by the
          European Space Agency (ESA) via Google Earth Engine. This is the
          surface reflectance product with atmospheric correction already
          applied -- so we&apos;re working with clean, calibrated data from
          2015 to present. Lake boundary polygons are loaded by the site
          operator when setting up a city.
        </p>

        {/* Attribution callout — rendered from city.config.json */}
        <div className="border-l-4 border-blue-500 pl-4 py-2 bg-white/5 rounded-r-lg my-6 space-y-2">
          {ATTRIBUTION.map((line) => (
            <p key={line} className="text-foreground/80 leading-relaxed">
              {line}
            </p>
          ))}
        </div>

        {/* Limitations */}
        <h2 className="text-2xl font-bold text-white mb-4 mt-12">
          Limitations &amp; caveats
        </h2>
        <p className="text-foreground/80 leading-relaxed mb-4">
          This is satellite data, not magic. Here&apos;s what you should know:
        </p>

        <ul className="list-disc list-inside text-foreground/70 space-y-3 mb-4">
          <li>
            <strong className="text-white">Resolution.</strong> Sentinel-2 has
            10-meter resolution. Each pixel covers 100m&sup2;. Lakes smaller
            than ~0.5 hectares are unreliable -- there just aren&apos;t enough
            pixels to work with.
          </li>
          <li>
            <strong className="text-white">Cloud cover.</strong> Cloudy seasons
            mean sparse usable images. We can&apos;t change the weather.
          </li>
          <li>
            <strong className="text-white">Proxy measurements.</strong> NDWI and
            NDVI are satellite-derived estimates, not ground truth water quality
            measurements. We&apos;re looking at reflectance patterns, not
            testing the water in a lab.
          </li>
          <li>
            <strong className="text-white">Not encroachment detection.</strong>{" "}
            This project tracks lake health -- water area and algae levels. It
            does not attempt to identify encroachment.
          </li>
          <li>
            <strong className="text-white">Update frequency.</strong> New
            satellite images every ~5 days, weather permitting. This is not
            real-time monitoring.
          </li>
        </ul>

        {/* Run it for your city */}
        <h2 className="text-2xl font-bold text-white mb-4 mt-12">
          Run this for your city
        </h2>
        <p className="text-foreground/80 leading-relaxed mb-4">
          {BRAND} is built on{" "}
          <strong className="text-white">LakeWatch</strong>, an open-source
          template for tracking any city&apos;s lakes from space. The pipeline,
          API, and this frontend are all generic: you provide a config file
          with your city&apos;s name, map center, and attribution, plus a
          GeoJSON of lake boundaries, and the same site you&apos;re looking at
          runs for your city.
        </p>
        <p className="text-foreground/80 leading-relaxed mb-4">
          The satellite data is free. The codebase is open source. If you want
          this for your city, everything you need is in the repo:{" "}
          <a
            href="https://github.com/0x101/lakewatch"
            className="text-blue-400 hover:text-blue-300 underline"
            target="_blank"
            rel="noopener noreferrer"
          >
            github.com/0x101/lakewatch
          </a>
        </p>

        {/* Credits */}
        <h2 className="text-2xl font-bold text-white mb-4 mt-12">
          Credits &amp; acknowledgments
        </h2>
        <div className="space-y-4 text-foreground/80 leading-relaxed">
          <p>
            This project would not be possible without the open data and open
            science ecosystems that make civic technology viable:
          </p>
          <ul className="list-disc list-inside space-y-2 text-foreground/70">
            <li>
              <strong className="text-white">European Space Agency (ESA)</strong> —
              for making Sentinel-2 imagery freely available to anyone through the
              Copernicus programme. This is what happens when a space agency decides
              that Earth observation data should be a public good.
            </li>
            <li>
              <strong className="text-white">Google Earth Engine</strong> — for
              providing the compute infrastructure to process petabytes of satellite
              imagery without downloading a single file. The free tier for non-commercial
              use is genuinely transformative.
            </li>
          </ul>
        </div>

        {/* Built with */}
        <h2 className="text-2xl font-bold text-white mb-4 mt-12">
          Built with
        </h2>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3 mb-6">
          {[
            { name: "Sentinel-2", desc: "Satellite imagery" },
            { name: "Google Earth Engine", desc: "Geospatial compute" },
            { name: "Python", desc: "Pipeline & analysis" },
            { name: "PostgreSQL + PostGIS", desc: "Spatial database" },
            { name: "FastAPI", desc: "REST API" },
            { name: "Next.js", desc: "Frontend framework" },
            { name: "Mapbox GL", desc: "Map rendering" },
            { name: "Recharts", desc: "Time-series charts" },
            { name: "Tailwind CSS", desc: "Styling" },
          ].map((tech) => (
            <div
              key={tech.name}
              className="bg-white/5 border border-white/10 rounded-lg px-3 py-2"
            >
              <p className="text-sm font-medium text-white">{tech.name}</p>
              <p className="text-xs text-foreground/40">{tech.desc}</p>
            </div>
          ))}
        </div>

        <p className="text-foreground/80 leading-relaxed mb-4">
          The entire codebase is open source. The satellite data is free. If
          you want to build something similar for another city, everything you
          need is here.
        </p>

        <p className="text-foreground/60 leading-relaxed text-sm mt-8">
          Have questions, spotted a bug, or want to help?{" "}
          <a
            href="https://github.com/0x101/lakewatch"
            className="text-blue-400 hover:text-blue-300 underline"
            target="_blank"
            rel="noopener noreferrer"
          >
            Check out the repo on GitHub.
          </a>
        </p>

        <div className="mt-12 pt-6 border-t border-white/10 text-xs text-foreground/30 space-y-1">
          <p>
            {BRAND} is an independent civic project. It is not affiliated with
            or endorsed by any government agency. All data is derived from
            publicly available sources.
          </p>
          <p>
            Sentinel-2 data: &copy; ESA, Copernicus Sentinel data.
          </p>
        </div>
      </article>
    </main>
  );
}
