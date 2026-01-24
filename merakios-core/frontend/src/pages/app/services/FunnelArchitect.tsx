import { useState } from "react";
import { Helmet } from "react-helmet-async";
import { 
  Network, 
  Zap, 
  GitBranch, 
  ArrowRight, 
  Plus,
  MousePointer2,
  Mail,
  FileText,
  DollarSign,
  AlertTriangle,
  CheckCircle2,
  ChevronRight,
  Grip,
  Eye,
  Play
} from "lucide-react";
import { 
  SiFacebook, 
  SiInstagram, 
  SiLinkedin, 
  SiTiktok 
} from "react-icons/si";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

// Smart Card Node Types
const nodeTypes = [
  { 
    id: "ad-facebook", 
    label: "Facebook Ad", 
    icon: SiFacebook, 
    color: "text-blue-500", 
    bgColor: "bg-blue-500/10", 
    borderColor: "border-blue-500/30",
    category: "ads" 
  },
  { 
    id: "ad-instagram", 
    label: "Instagram Ad", 
    icon: SiInstagram, 
    color: "text-pink-500", 
    bgColor: "bg-pink-500/10", 
    borderColor: "border-pink-500/30",
    category: "ads" 
  },
  { 
    id: "ad-linkedin", 
    label: "LinkedIn Ad", 
    icon: SiLinkedin, 
    color: "text-blue-600", 
    bgColor: "bg-blue-600/10", 
    borderColor: "border-blue-600/30",
    category: "ads" 
  },
  { 
    id: "ad-tiktok", 
    label: "TikTok Ad", 
    icon: SiTiktok, 
    color: "text-pink-400", 
    bgColor: "bg-pink-400/10", 
    borderColor: "border-pink-400/30",
    category: "ads" 
  },
  { 
    id: "landing", 
    label: "Landing Page", 
    icon: FileText, 
    color: "text-purple-400", 
    bgColor: "bg-purple-400/10", 
    borderColor: "border-purple-400/30",
    category: "pages" 
  },
  { 
    id: "email", 
    label: "Email Sequence", 
    icon: Mail, 
    color: "text-amber-400", 
    bgColor: "bg-amber-400/10", 
    borderColor: "border-amber-400/30",
    category: "automation" 
  },
  { 
    id: "checkout", 
    label: "Checkout", 
    icon: DollarSign, 
    color: "text-green-400", 
    bgColor: "bg-green-400/10", 
    borderColor: "border-green-400/30",
    category: "conversion" 
  },
];

// Sample funnel nodes for preview
const sampleNodes = [
  { id: 1, type: "ad-facebook", x: 60, y: 80, status: "active", metrics: { ctr: "3.2%", spend: "$45" } },
  { id: 2, type: "ad-instagram", x: 60, y: 180, status: "active", metrics: { ctr: "4.1%", spend: "$32" } },
  { id: 3, type: "landing", x: 220, y: 130, status: "warning", metrics: { conv: "12%", visits: "1.2k" } },
  { id: 4, type: "email", x: 380, y: 80, status: "active", metrics: { open: "45%", clicks: "320" } },
  { id: 5, type: "checkout", x: 540, y: 130, status: "active", metrics: { conv: "8%", sales: "$2.4k" } },
];

// Smart Card Component
const SmartCard = ({ node, nodeType, isSelected, onSelect }: { 
  node: typeof sampleNodes[0], 
  nodeType: typeof nodeTypes[0],
  isSelected: boolean,
  onSelect: () => void 
}) => {
  const statusColors = {
    active: "border-green-500/50 shadow-green-500/20",
    warning: "border-amber-500/50 shadow-amber-500/20",
    error: "border-red-500/50 shadow-red-500/20",
  };

  const statusIndicator = {
    active: <CheckCircle2 className="w-3 h-3 text-green-400" />,
    warning: <AlertTriangle className="w-3 h-3 text-amber-400" />,
    error: <AlertTriangle className="w-3 h-3 text-red-400" />,
  };

  return (
    <div 
      className={`absolute cursor-pointer transition-all duration-300 ${isSelected ? 'scale-105 z-10' : 'hover:scale-102'}`}
      style={{ left: node.x, top: node.y }}
      onClick={onSelect}
    >
      <div className={`
        w-32 p-3 rounded-xl backdrop-blur-xl 
        bg-gradient-to-br from-card/90 to-card/70 
        border-2 ${statusColors[node.status as keyof typeof statusColors]}
        shadow-lg hover:shadow-xl
        ${isSelected ? 'ring-2 ring-primary ring-offset-2 ring-offset-background' : ''}
      `}>
        {/* Header */}
        <div className="flex items-center justify-between mb-2">
          <div className={`w-8 h-8 rounded-lg ${nodeType.bgColor} flex items-center justify-center`}>
            <nodeType.icon className={`w-4 h-4 ${nodeType.color}`} />
          </div>
          <div className="flex items-center gap-1">
            {statusIndicator[node.status as keyof typeof statusIndicator]}
          </div>
        </div>
        
        {/* Label */}
        <p className="text-xs font-medium mb-2 truncate">{nodeType.label}</p>
        
        {/* Metrics preview */}
        <div className="flex gap-2 text-[10px]">
          {Object.entries(node.metrics).slice(0, 2).map(([key, value]) => (
            <div key={key} className="px-1.5 py-0.5 rounded bg-muted/50">
              <span className="text-muted-foreground">{key}:</span>{" "}
              <span className="text-foreground font-medium">{value}</span>
            </div>
          ))}
        </div>
        
        {/* Connection points */}
        <div className="absolute -right-2 top-1/2 -translate-y-1/2 w-4 h-4 rounded-full bg-primary border-2 border-background shadow-lg" />
        <div className="absolute -left-2 top-1/2 -translate-y-1/2 w-4 h-4 rounded-full bg-muted border-2 border-background shadow-lg" />
      </div>
    </div>
  );
};

// Connection Line with Particles
const ConnectionLine = ({ from, to, status = "active" }: { from: { x: number, y: number }, to: { x: number, y: number }, status?: string }) => {
  const midX = (from.x + to.x) / 2;
  const controlY1 = from.y;
  const controlY2 = to.y;
  
  const pathD = `M ${from.x} ${from.y} C ${midX} ${controlY1}, ${midX} ${controlY2}, ${to.x} ${to.y}`;
  
  const gradientId = `gradient-${from.x}-${to.x}`;
  const particleId = `particle-${from.x}-${to.x}`;
  
  return (
    <g>
      <defs>
        <linearGradient id={gradientId} x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stopColor={status === "active" ? "hsl(var(--primary))" : "hsl(var(--muted))"} />
          <stop offset="100%" stopColor={status === "active" ? "hsl(var(--accent))" : "hsl(var(--muted))"} />
        </linearGradient>
        <filter id="glow-line">
          <feGaussianBlur stdDeviation="2" result="coloredBlur"/>
          <feMerge>
            <feMergeNode in="coloredBlur"/>
            <feMergeNode in="SourceGraphic"/>
          </feMerge>
        </filter>
      </defs>
      
      {/* Main cable */}
      <path 
        d={pathD} 
        stroke={`url(#${gradientId})`}
        strokeWidth="3" 
        fill="none"
        filter="url(#glow-line)"
        strokeLinecap="round"
      />
      
      {/* Animated particle */}
      {status === "active" && (
        <circle r="4" fill="hsl(var(--accent))">
          <animateMotion dur="2s" repeatCount="indefinite">
            <mpath href={`#path-${particleId}`} />
          </animateMotion>
        </circle>
      )}
      
      {/* Hidden path for animation reference */}
      <path id={`path-${particleId}`} d={pathD} fill="none" stroke="none" />
    </g>
  );
};

const FunnelArchitect = () => {
  const [selectedNode, setSelectedNode] = useState<number | null>(null);
  const [isPreviewMode, setIsPreviewMode] = useState(false);

  const connections = [
    { from: { x: 140, y: 110 }, to: { x: 220, y: 160 }, status: "active" },
    { from: { x: 140, y: 210 }, to: { x: 220, y: 160 }, status: "active" },
    { from: { x: 300, y: 160 }, to: { x: 380, y: 110 }, status: "warning" },
    { from: { x: 460, y: 110 }, to: { x: 540, y: 160 }, status: "active" },
  ];

  return (
    <>
      <Helmet>
        <title>Arquitecto de Embudos - MerakiOS</title>
      </Helmet>

      <div className="space-y-6 animate-fade-in-up">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-blue-500/20 to-cyan-500/10 border border-blue-500/30 flex items-center justify-center">
              <Network className="w-7 h-7 text-blue-400" />
            </div>
            <div>
              <div className="flex items-center gap-3">
                <h1 className="font-display text-3xl font-bold">Arquitecto de Embudos</h1>
                <Badge variant="outline" className="font-mono text-xs">The Mapper</Badge>
              </div>
              <p className="text-muted-foreground">Flow Builder visual con tarjetas inteligentes</p>
            </div>
          </div>
          
          <div className="flex items-center gap-3">
            <Button variant="outline" onClick={() => setIsPreviewMode(!isPreviewMode)}>
              {isPreviewMode ? <Eye className="w-4 h-4 mr-2" /> : <Play className="w-4 h-4 mr-2" />}
              {isPreviewMode ? "Vista Previa" : "Modo Edición"}
            </Button>
            <Button className="gradient-primary">
              <Plus className="w-4 h-4 mr-2" />
              Nuevo Embudo
            </Button>
          </div>
        </div>

        <div className="grid lg:grid-cols-[280px_1fr] gap-6">
          {/* Sidebar - Drag & Drop Panel */}
          <Card className="bg-card/50 border-border h-fit">
            <CardHeader className="pb-3">
              <CardTitle className="text-base flex items-center gap-2">
                <Grip className="w-4 h-4 text-muted-foreground" />
                Elementos
              </CardTitle>
              <CardDescription className="text-xs">Arrastra al canvas</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Ads */}
              <div>
                <p className="text-xs text-muted-foreground uppercase tracking-wider mb-3">Anuncios</p>
                <div className="space-y-2">
                  {nodeTypes.filter(n => n.category === "ads").map((node) => (
                    <div 
                      key={node.id}
                      className={`flex items-center gap-3 p-3 rounded-xl ${node.bgColor} border ${node.borderColor} cursor-grab hover:scale-[1.02] transition-transform`}
                      draggable
                    >
                      <div className="w-8 h-8 rounded-lg bg-background/50 flex items-center justify-center">
                        <node.icon className={`w-4 h-4 ${node.color}`} />
                      </div>
                      <span className="text-sm font-medium">{node.label}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Pages */}
              <div>
                <p className="text-xs text-muted-foreground uppercase tracking-wider mb-3">Páginas</p>
                <div className="space-y-2">
                  {nodeTypes.filter(n => n.category === "pages").map((node) => (
                    <div 
                      key={node.id}
                      className={`flex items-center gap-3 p-3 rounded-xl ${node.bgColor} border ${node.borderColor} cursor-grab hover:scale-[1.02] transition-transform`}
                      draggable
                    >
                      <div className="w-8 h-8 rounded-lg bg-background/50 flex items-center justify-center">
                        <node.icon className={`w-4 h-4 ${node.color}`} />
                      </div>
                      <span className="text-sm font-medium">{node.label}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Automation */}
              <div>
                <p className="text-xs text-muted-foreground uppercase tracking-wider mb-3">Automatización</p>
                <div className="space-y-2">
                  {nodeTypes.filter(n => n.category === "automation").map((node) => (
                    <div 
                      key={node.id}
                      className={`flex items-center gap-3 p-3 rounded-xl ${node.bgColor} border ${node.borderColor} cursor-grab hover:scale-[1.02] transition-transform`}
                      draggable
                    >
                      <div className="w-8 h-8 rounded-lg bg-background/50 flex items-center justify-center">
                        <node.icon className={`w-4 h-4 ${node.color}`} />
                      </div>
                      <span className="text-sm font-medium">{node.label}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Conversion */}
              <div>
                <p className="text-xs text-muted-foreground uppercase tracking-wider mb-3">Conversión</p>
                <div className="space-y-2">
                  {nodeTypes.filter(n => n.category === "conversion").map((node) => (
                    <div 
                      key={node.id}
                      className={`flex items-center gap-3 p-3 rounded-xl ${node.bgColor} border ${node.borderColor} cursor-grab hover:scale-[1.02] transition-transform`}
                      draggable
                    >
                      <div className="w-8 h-8 rounded-lg bg-background/50 flex items-center justify-center">
                        <node.icon className={`w-4 h-4 ${node.color}`} />
                      </div>
                      <span className="text-sm font-medium">{node.label}</span>
                    </div>
                  ))}
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Canvas */}
          <Card className="bg-card/30 border-border overflow-hidden min-h-[600px]">
            <CardHeader className="border-b border-border/50 bg-card/50">
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="flex items-center gap-2">
                    <GitBranch className="w-5 h-5 text-primary" />
                    Canvas del Embudo
                  </CardTitle>
                  <CardDescription>Embudo de ventas principal</CardDescription>
                </div>
                <div className="flex items-center gap-4">
                  <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-green-500/10 border border-green-500/30">
                    <CheckCircle2 className="w-4 h-4 text-green-400" />
                    <span className="text-xs text-green-400 font-medium">3 Activos</span>
                  </div>
                  <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-amber-500/10 border border-amber-500/30">
                    <AlertTriangle className="w-4 h-4 text-amber-400" />
                    <span className="text-xs text-amber-400 font-medium">1 Alerta</span>
                  </div>
                </div>
              </div>
            </CardHeader>
            <CardContent className="p-0 relative">
              {/* Grid background */}
              <div 
                className="absolute inset-0 opacity-20"
                style={{
                  backgroundImage: `
                    linear-gradient(hsl(var(--border)) 1px, transparent 1px),
                    linear-gradient(90deg, hsl(var(--border)) 1px, transparent 1px)
                  `,
                  backgroundSize: '40px 40px'
                }}
              />
              
              {/* Canvas content */}
              <div className="relative h-[500px] overflow-hidden">
                {/* Connection SVG Layer */}
                <svg className="absolute inset-0 w-full h-full pointer-events-none">
                  {connections.map((conn, index) => (
                    <ConnectionLine 
                      key={index}
                      from={conn.from}
                      to={conn.to}
                      status={conn.status}
                    />
                  ))}
                </svg>
                
                {/* Smart Cards Layer */}
                {sampleNodes.map((node) => {
                  const nodeType = nodeTypes.find(t => t.id === node.type);
                  if (!nodeType) return null;
                  
                  return (
                    <SmartCard
                      key={node.id}
                      node={node}
                      nodeType={nodeType}
                      isSelected={selectedNode === node.id}
                      onSelect={() => setSelectedNode(node.id)}
                    />
                  );
                })}
                
                {/* Floating instructions */}
                <div className="absolute bottom-4 left-4 flex items-center gap-2 px-3 py-2 rounded-lg bg-card/90 border border-border/50 backdrop-blur-sm">
                  <MousePointer2 className="w-4 h-4 text-muted-foreground" />
                  <span className="text-xs text-muted-foreground">Click para seleccionar • Arrastra para mover</span>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Coming Soon Banner */}
        <Card className="bg-gradient-to-r from-blue-500/10 to-cyan-500/10 border-blue-500/20">
          <CardContent className="py-6">
            <div className="flex flex-col md:flex-row items-center justify-between gap-4">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 rounded-full bg-blue-500/20 flex items-center justify-center">
                  <Zap className="w-6 h-6 text-blue-400" />
                </div>
                <div>
                  <h3 className="font-display font-semibold">Editor Interactivo Completo</h3>
                  <p className="text-sm text-muted-foreground">Próximamente: Drag & drop real, conexiones dinámicas y más</p>
                </div>
              </div>
              <Button variant="outline" disabled>
                En desarrollo
                <ArrowRight className="w-4 h-4 ml-2" />
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </>
  );
};

export default FunnelArchitect;
