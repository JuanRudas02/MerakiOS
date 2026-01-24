const AbstractNodes = ({ variant = "dark" }: { variant?: "dark" | "light" }) => {
  const baseColor = variant === "dark" ? "hsl(217 82% 50%)" : "hsl(217 82% 50%)";
  const accentColor = variant === "dark" ? "hsl(191 100% 50%)" : "hsl(250 100% 65%)";
  
  return (
    <svg
      className="absolute inset-0 w-full h-full overflow-visible"
      viewBox="0 0 400 800"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      preserveAspectRatio="xMidYMid slice"
    >
      <defs>
        <linearGradient id={`nodeGrad-${variant}`} x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor={baseColor} />
          <stop offset="100%" stopColor={accentColor} />
        </linearGradient>
        <filter id={`blur-${variant}`}>
          <feGaussianBlur stdDeviation="2" />
        </filter>
      </defs>
      
      {/* Connection lines */}
      <g opacity="0.3">
        <line x1="50" y1="100" x2="150" y2="200" stroke={baseColor} strokeWidth="1" />
        <line x1="150" y1="200" x2="100" y2="350" stroke={baseColor} strokeWidth="1" />
        <line x1="100" y1="350" x2="200" y2="450" stroke={baseColor} strokeWidth="1" />
        <line x1="200" y1="450" x2="150" y2="600" stroke={baseColor} strokeWidth="1" />
        <line x1="300" y1="150" x2="350" y2="300" stroke={accentColor} strokeWidth="1" />
        <line x1="350" y1="300" x2="280" y2="450" stroke={accentColor} strokeWidth="1" />
        <line x1="280" y1="450" x2="320" y2="600" stroke={accentColor} strokeWidth="1" />
        <line x1="150" y1="200" x2="300" y2="150" stroke={baseColor} strokeWidth="0.5" strokeDasharray="5,5" />
        <line x1="200" y1="450" x2="280" y2="450" stroke={accentColor} strokeWidth="0.5" strokeDasharray="5,5" />
      </g>
      
      {/* Nodes */}
      <g>
        <circle cx="50" cy="100" r="4" fill={baseColor} className="animate-node-pulse" />
        <circle cx="150" cy="200" r="6" fill={`url(#nodeGrad-${variant})`} className="animate-node-pulse" style={{ animationDelay: "0.3s" }} />
        <circle cx="100" cy="350" r="5" fill={baseColor} className="animate-node-pulse" style={{ animationDelay: "0.6s" }} />
        <circle cx="200" cy="450" r="7" fill={`url(#nodeGrad-${variant})`} className="animate-node-pulse" style={{ animationDelay: "0.9s" }} />
        <circle cx="150" cy="600" r="4" fill={baseColor} className="animate-node-pulse" style={{ animationDelay: "1.2s" }} />
        
        <circle cx="300" cy="150" r="5" fill={accentColor} className="animate-node-pulse" style={{ animationDelay: "0.2s" }} />
        <circle cx="350" cy="300" r="6" fill={`url(#nodeGrad-${variant})`} className="animate-node-pulse" style={{ animationDelay: "0.5s" }} />
        <circle cx="280" cy="450" r="4" fill={accentColor} className="animate-node-pulse" style={{ animationDelay: "0.8s" }} />
        <circle cx="320" cy="600" r="5" fill={`url(#nodeGrad-${variant})`} className="animate-node-pulse" style={{ animationDelay: "1.1s" }} />
      </g>
      
      {/* Floating hexagons */}
      <g opacity="0.2">
        <polygon
          points="320,80 340,92 340,116 320,128 300,116 300,92"
          fill="none"
          stroke={baseColor}
          strokeWidth="1"
          className="animate-float"
        />
        <polygon
          points="80,500 105,515 105,545 80,560 55,545 55,515"
          fill="none"
          stroke={accentColor}
          strokeWidth="1"
          className="animate-float"
          style={{ animationDelay: "2s" }}
        />
        <polygon
          points="360,520 380,532 380,556 360,568 340,556 340,532"
          fill="none"
          stroke={baseColor}
          strokeWidth="1"
          className="animate-float"
          style={{ animationDelay: "4s" }}
        />
      </g>
    </svg>
  );
};

export default AbstractNodes;
